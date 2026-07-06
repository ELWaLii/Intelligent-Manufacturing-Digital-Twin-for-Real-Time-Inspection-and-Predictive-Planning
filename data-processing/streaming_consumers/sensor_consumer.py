"""KAVE CNC Digital Twin — Real-Time Kafka Sensor Consumer & LSTM Inference.

This module implements the streaming inference pipeline for the CNC
Digital Twin.  It spawns one consumer thread per virtual machine, each
subscribing to the machine's dedicated Kafka topic
(``cnc_telemetry_<machine_id>``).

For every incoming telemetry message the consumer:

1. Appends the reading to a per-machine circular buffer.
2. Once the buffer is full (``window_size + seq_length`` rows), it
   extracts rolling statistical features (standard deviation and RMS)
   over a sliding window.
3. Scales the features with the saved ``StandardScaler``.
4. Reshapes the most recent ``seq_length`` timesteps into an LSTM input
   tensor and runs ``model.predict()`` to obtain wear-stage
   probabilities.
5. Writes the prediction (stage, confidence, and selected raw readings)
   to InfluxDB as a ``machine_health`` measurement for real-time
   Grafana dashboards.

Environment variables (all optional — sensible defaults are provided):
    KAFKA_BOOTSTRAP_SERVERS  Kafka broker address (default ``localhost:9092``).
    INFLUX_URL               InfluxDB HTTP endpoint (default ``http://127.0.0.1:8089``).
    INFLUX_TOKEN             InfluxDB authentication token.
    INFLUX_ORG               InfluxDB organisation (default ``kave_org``).
    INFLUX_BUCKET            InfluxDB bucket (default ``cnc_digital_twin``).
"""

import json
import os
import time
import logging
import threading
from collections import deque
import numpy as np
import pandas as pd
import joblib
from kafka import KafkaConsumer
from tensorflow.keras.models import load_model
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("kave.consumer")

# ---------------------------------------------------------------------------
# InfluxDB configuration — falls back to environment variables with defaults
# ---------------------------------------------------------------------------
INFLUX_URL = os.environ.get("INFLUX_URL", "http://127.0.0.1:8089")
INFLUX_TOKEN = os.environ.get(
    "INFLUX_TOKEN",
    "t4Zac1hxXZQvIIfeBCoJLJgxJwWIPDPTknBSl54o1erJHqfG3vPdr0RVZocUGIrfSppVa5nF4gXyKbxEnVJRQA==",
)
INFLUX_ORG = os.environ.get("INFLUX_ORG", "kave_org")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "cnc_digital_twin")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

db_write_lock = threading.Lock()

logger.info("Connected to InfluxDB successfully on %s", INFLUX_URL)

# ---------------------------------------------------------------------------
# Model & scaler loading with error handling
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

model_path = os.path.join(BASE_DIR, 'cnc_lstm_model.keras')
scaler_path = os.path.join(BASE_DIR, 'cnc_scaler.pkl')
features_path = os.path.join(BASE_DIR, 'model_features.pkl')

logger.info("Loading model and training tools from the current directory...")

try:
    model = load_model(model_path)
    logger.info("LSTM model loaded from %s", model_path)
except Exception as e:
    logger.error("Failed to load LSTM model from %s: %s", model_path, e)
    raise

try:
    scaler = joblib.load(scaler_path)
    logger.info("Scaler loaded from %s", scaler_path)
except Exception as e:
    logger.error("Failed to load scaler from %s: %s", scaler_path, e)
    raise

try:
    features_extracted = joblib.load(features_path)
    logger.info("Feature list loaded from %s", features_path)
except Exception as e:
    logger.error("Failed to load feature list from %s: %s", features_path, e)
    raise

logger.info("LSTM Model and Tools loaded successfully. Waiting for live data...")

# ---------------------------------------------------------------------------
# Threading lock for TensorFlow model.predict() — TensorFlow/Keras is not
# guaranteed to be thread-safe, so concurrent predict calls from multiple
# consumer threads must be serialised.
# ---------------------------------------------------------------------------
model_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Feature & buffer configuration
# ---------------------------------------------------------------------------

# Raw sensor columns used for rolling-window feature extraction.
features_to_use = ['X1_OutputCurrent', 'Y1_OutputCurrent', 'Z1_OutputCurrent', 'S1_OutputPower']

# Number of rows used to compute each rolling statistic (std, rms).
window_size = 10

# Number of consecutive timesteps the LSTM expects as a single input sequence.
seq_length = 10

# The circular buffer must hold enough rows so that after applying the
# rolling window (which consumes ``window_size - 1`` rows to NaN) there
# are still ``seq_length`` valid feature rows remaining.
buffer_size = window_size + seq_length

buffer_lock = threading.Lock()
machine_buffers = {}

KAFKA_BROKER = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')


def machine_consumer_worker(machine_id):
    """Consume telemetry from Kafka and run LSTM inference for one machine.

    This function is designed to run inside a dedicated
    ``threading.Thread``.  It subscribes to the Kafka topic
    ``cnc_telemetry_<machine_id>``, maintains a per-machine circular
    buffer, computes rolling statistical features once the buffer is
    full, feeds them through the pre-trained LSTM model, and writes the
    resulting wear-stage prediction to InfluxDB.

    Args:
        machine_id: Identifier of the virtual CNC machine to monitor,
            e.g. ``"CNC_VIRTUAL_01"``.
    """
    topic_name = f"cnc_telemetry_{machine_id}"
    logger.info("Thread started and listening to: %s", topic_name)

    consumer = KafkaConsumer(
        topic_name,
        bootstrap_servers=[KAFKA_BROKER],
        auto_offset_reset='latest',
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

    for message in consumer:
        try:
            live_data = message.value

            # Append the new reading to a thread-safe per-machine buffer.
            with buffer_lock:
                if machine_id not in machine_buffers:
                    machine_buffers[machine_id] = deque(maxlen=buffer_size)
                machine_buffers[machine_id].append(live_data)
                current_len = len(machine_buffers[machine_id])
                # Snapshot the buffer so we can release the lock quickly.
                local_buffer_snapshot = list(machine_buffers[machine_id])

            logger.info("[%s] -> Received data | Buffer status: (%d/%d)",
                        topic_name, current_len, buffer_size)

            # Wait until the buffer is full before attempting inference.
            if current_len < buffer_size:
                continue

            df_buffer = pd.DataFrame(local_buffer_snapshot)

            # --- Rolling-window feature extraction ---
            # For each raw sensor column, compute a rolling standard
            # deviation and root-mean-square (RMS) over the last
            # ``window_size`` readings.  These derived features capture
            # short-term signal variability which is indicative of
            # mechanical wear and vibration changes.
            for col in features_to_use:
                if col in df_buffer.columns:
                    df_buffer[f'{col}_std'] = df_buffer[col].rolling(window=window_size).std()
                    df_buffer[f'{col}_rms'] = np.sqrt((df_buffer[col]**2).rolling(window=window_size).mean())

            # Drop the initial rows that contain NaN due to the rolling
            # window warm-up period.
            df_features = df_buffer.dropna().copy()

            if len(df_features) >= seq_length:
                # --- LSTM sequence preparation ---
                # Select only the engineered feature columns used during
                # training, take the most recent ``seq_length`` rows,
                # scale them with the saved StandardScaler, and reshape
                # into the 3-D tensor (1, seq_length, n_features) that
                # the LSTM expects.
                df_seq = df_features[features_extracted].tail(seq_length)
                seq_scaled = scaler.transform(df_seq)
                X_live = seq_scaled.reshape(1, seq_length, len(features_extracted))

                # Serialise model.predict() calls — TensorFlow is not
                # thread-safe for concurrent inference.
                with model_lock:
                    probabilities = model.predict(X_live, verbose=0)[0]

                predicted_stage = int(np.argmax(probabilities))
                confidence = float(probabilities[predicted_stage] * 100)

                point = (
                    Point("machine_health")
                    .tag("machine_id", machine_id)
                    .tag("process", live_data.get('Machining_Process', 'Unknown'))
                    .field("prediction_stage", predicted_stage)
                    .field("confidence_percent", confidence)
                    .field("x1_current", float(live_data.get('X1_OutputCurrent', 0)))
                    .field("z1_current", float(live_data.get('Z1_OutputCurrent', 0)))
                    .time(time.time_ns(), WritePrecision.NS)
                )

                with db_write_lock:
                    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)

                if predicted_stage == 3:
                    logger.critical("CRITICAL: %s WORN OUT! Stop Machine! Confidence: %.1f%%",
                                    machine_id, confidence)
                elif predicted_stage == 2:
                    logger.warning("WARNING: %s Severe Wear Detected. Confidence: %.1f%%",
                                   machine_id, confidence)
                elif predicted_stage == 1:
                    logger.info("INFO: %s Initial Wear Started. Confidence: %.1f%%",
                                machine_id, confidence)
                else:
                    logger.info("OK: %s Tool is Healthy. Confidence: %.1f%%",
                                machine_id, confidence)

        except Exception as e:
            logger.error("ERROR in Thread %s during live processing: %s", machine_id, e)


if __name__ == "__main__":
    machines_list = ['CNC_VIRTUAL_01', 'CNC_VIRTUAL_02', 'CNC_VIRTUAL_03', 'CNC_VIRTUAL_04']
    active_threads = []

    logger.info("Starting Parallel Real-Time Consumers Pipeline...")

    for m_id in machines_list:
        thread = threading.Thread(target=machine_consumer_worker, args=(m_id,))
        thread.daemon = True
        active_threads.append(thread)
        thread.start()
        time.sleep(0.2)

    logger.info("All parallel consumers are online and listening! Press Ctrl+C to exit.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping Parallel Consumers Pipeline...")

        # Close the InfluxDB client to release network resources and
        # flush any pending writes.
        try:
            client.close()
            logger.info("InfluxDB client closed successfully.")
        except Exception as e:
            logger.warning("Error closing InfluxDB client: %s", e)

        logger.info("Done.")