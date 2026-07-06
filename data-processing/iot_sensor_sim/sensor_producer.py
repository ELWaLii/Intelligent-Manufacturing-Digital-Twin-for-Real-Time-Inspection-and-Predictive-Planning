"""KAVE CNC Digital Twin — Multi-Machine Kafka Sensor Producer.

This module simulates real-time CNC telemetry for four virtual machines
(CNC_VIRTUAL_01 through CNC_VIRTUAL_04).  Each machine runs in its own
thread, generating randomised sensor readings (position, velocity,
acceleration, current, voltage, power, clamp pressure, etc.) and
publishing them to a per-machine Kafka topic.

Readings are also batched locally and periodically flushed to a Parquet
file (``cnc_historical_data.parquet``) for offline analytics.

CNC_VIRTUAL_02 is intentionally configured to simulate progressive tool
wear across four timed phases so that downstream LSTM models can be
validated against a realistic degradation curve.

Usage::

    python sensor_producer.py          # starts all four virtual machines
    KAFKA_BOOTSTRAP_SERVERS=broker:9092 python sensor_producer.py

Environment variables:
    KAFKA_BOOTSTRAP_SERVERS  Kafka broker address (default ``localhost:9092``).
"""

import pandas as pd
import json
import time
import random
import os
import logging
import signal
import threading
from kafka import KafkaProducer
import pyarrow as pa
import pyarrow.parquet as pq

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("kave.producer")

# ---------------------------------------------------------------------------
# Module-level threading event used to signal all worker threads to stop.
# Declared at module scope so that every function can reference it without
# requiring it to be passed as an argument or declared ``global`` inside
# ``__main__``.
# ---------------------------------------------------------------------------
stop_event = threading.Event()

# ---------------------------------------------------------------------------
# Kafka producer
# ---------------------------------------------------------------------------
KAFKA_BROKER = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')

try:
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_BROKER],
        value_serializer=lambda x: json.dumps(x).encode('utf-8'),
        max_block_ms=2000
    )
    logger.info("Kafka Producer initialized successfully.")
except Exception as e:
    logger.error("Kafka Initialization Error: %s", e)
    producer = None

# ---------------------------------------------------------------------------
# Parquet output path & buffering
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
parquet_file = os.path.join(BASE_DIR, 'cnc_historical_data.parquet')

batch_size = 10
data_buffer = []
buffer_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Sensor value ranges per axis (derived from real CNC machine envelopes)
# ---------------------------------------------------------------------------
sensor_ranges = {
    'X1': {'pos': (141.0, 198.0), 'vel': (-20.4, 50.7), 'acc': (-1280, 1440), 'volt': (320, 331)},
    'Y1': {'pos': (72.4, 158.0), 'vel': (-32.8, 50.4), 'acc': (-1260, 1460), 'volt': (319, 333)},
    'Z1': {'pos': (27.5, 119.0), 'vel': (-51.5, 50.9), 'acc': (-1260, 1270), 'volt': (0, 0)},
    'S1': {'pos': (-2150, 2150), 'vel': (-0.06, 53.8), 'acc': (-150, 150), 'pwr': (0, 0.56)},
}

# Machine multiplier profiles — values > 1.0 exaggerate sensor readings,
# values < 1.0 dampen them.
machine_profiles = {
    "CNC_VIRTUAL_01": 1.0,
    "CNC_VIRTUAL_02": 1.0,
    "CNC_VIRTUAL_03": 1.35,
    "CNC_VIRTUAL_04": 0.75,
}


def generate_row(machine_id):
    """Generate a single simulated CNC telemetry row for *machine_id*.

    The row contains position, velocity, acceleration, current, voltage,
    and power readings for each axis (X1, Y1, Z1, S1) as well as
    programme metadata and a clamp-pressure reading.

    Args:
        machine_id: Identifier of the virtual CNC machine, e.g.
            ``"CNC_VIRTUAL_01"``.

    Returns:
        A ``dict`` whose keys are sensor column names and whose values
        are the randomly generated (but range-bounded) readings.
    """
    data = {}
    mult = machine_profiles.get(machine_id, 1.0)

    for axis in ['X1', 'Y1', 'Z1', 'S1']:
        base_pos = random.uniform(*sensor_ranges[axis]['pos']) * mult
        data[f'{axis}_ActualPosition'] = round(base_pos, 3)
        data[f'{axis}_CommandPosition'] = round(base_pos + random.uniform(-0.05, 0.05), 3)

        data[f'{axis}_ActualVelocity'] = round(random.uniform(*sensor_ranges[axis]['vel']) * mult, 3)
        data[f'{axis}_CommandVelocity'] = round(data[f'{axis}_ActualVelocity'] + random.uniform(-0.1, 0.1), 3)

        data[f'{axis}_ActualAcceleration'] = round(random.uniform(*sensor_ranges[axis]['acc']) * mult, 2)
        data[f'{axis}_CommandAcceleration'] = round(data[f'{axis}_ActualAcceleration'] + 1.0, 2)

        data[f'{axis}_CurrentFeedback'] = round(random.uniform(-5, 30) * mult, 3)
        data[f'{axis}_DCBusVoltage'] = round(random.uniform(0, 0.4), 4)

        data[f'{axis}_OutputCurrent'] = round(random.uniform(320, 330) * mult, 1)
        data[f'{axis}_OutputVoltage'] = round(random.uniform(0, 80) * mult, 2)

        if 'pwr' in sensor_ranges[axis]:
            data[f'{axis}_OutputPower'] = round(random.uniform(*sensor_ranges[axis]['pwr']) * mult, 6)

    data['M1_CURRENT_PROGRAM_NUMBER'] = 1.0
    data['M1_sequence_number'] = float(random.randint(1, 150))
    data['M1_CURRENT_FEEDRATE'] = float(random.choice([3, 6, 20, 50]))
    data['feedrate'] = data['M1_CURRENT_FEEDRATE']
    data['clamp_pressure'] = round(random.uniform(2.5, 4.0) * mult, 1)
    data['machine_id'] = machine_id
    data['event_timestamp'] = time.time()
    data['Machining_Process'] = random.choice(['Starting', 'Prep', 'Layer 1 Up', 'Layer 1 Down'])
    return data


def save_to_parquet(buffer_to_save):
    """Persist a list of telemetry dicts to the on-disk Parquet file.

    If the Parquet file already exists the new rows are **appended** by
    reading the existing table, concatenating the new batch, and
    rewriting the combined result.  This avoids the previous bug where
    only the latest batch would overwrite the file.

    Args:
        buffer_to_save: An iterable of ``dict`` objects, each
            representing a single telemetry row.
    """
    if not buffer_to_save:
        return
    try:
        df_batch = pd.DataFrame(list(buffer_to_save))
        new_table = pa.Table.from_pandas(df_batch)

        with buffer_lock:
            if os.path.isfile(parquet_file):
                # Read the existing data and concatenate the new batch
                # so that historical rows are never lost.
                existing_table = pq.read_table(parquet_file)
                combined_table = pa.concat_tables([existing_table, new_table],
                                                  promote_options="default")
                pq.write_table(combined_table, parquet_file, compression='snappy')
            else:
                # First write — create the file from scratch.
                pq.write_table(new_table, parquet_file, compression='snappy')

        logger.info("Parquet file updated successfully at: %s", parquet_file)
    except Exception as e:
        logger.error("HARD DISK WRITE ERROR: %s", e)


def machine_worker(machine_id):
    """Run the telemetry-generation loop for a single virtual CNC machine.

    This function is intended to be executed inside a dedicated
    ``threading.Thread``.  It continuously generates sensor rows via
    :func:`generate_row`, publishes each row to the machine's Kafka
    topic, and appends it to the shared ``data_buffer``.  When the
    buffer reaches ``batch_size`` rows the batch is flushed to Parquet.

    For ``CNC_VIRTUAL_02`` the function overlays a four-phase tool-wear
    simulation on top of the normal readings so that downstream anomaly
    detection models can observe a realistic degradation trajectory.

    Args:
        machine_id: Identifier of the virtual CNC machine to simulate,
            e.g. ``"CNC_VIRTUAL_02"``.
    """
    global data_buffer
    logger.info("Worker for %s started...", machine_id)
    machine_topic = f"cnc_telemetry_{machine_id}"

    start_time = time.time()

    # Each wear-simulation phase lasts this many seconds.
    phase_duration = 5

    while not stop_event.is_set():
        try:
            payload = generate_row(machine_id)

            # ----- CNC_VIRTUAL_02 progressive wear simulation -----
            # Four phases model the lifecycle of a cutting tool:
            #   Phase 1 (0–5 s)  : Healthy / normal operation — no
            #                      modifications to the base readings.
            #   Phase 2 (5–10 s) : Initial wear — current rises to
            #                      420–480 A, spindle power to 1.2–1.8.
            #   Phase 3 (10–15 s): Severe wear — current climbs to
            #                      650–750 A, power to 2.5–4.5, and
            #                      clamp pressure drops (0.5–1.0).
            #   Phase 4 (>15 s)  : Failure / worn out — extreme current
            #                      (1 600–1 900 A), very high power
            #                      (12.5–15.0), near-zero clamp pressure.
            if machine_id == "CNC_VIRTUAL_02":
                elapsed_time = time.time() - start_time

                if elapsed_time <= phase_duration:
                    # Phase 1 — healthy: use unmodified base readings.
                    pass

                elif elapsed_time <= (phase_duration * 2):
                    # Phase 2 — initial wear: moderate current & power rise.
                    payload['X1_OutputCurrent'] = round(random.uniform(420.0, 480.0), 1)
                    payload['Y1_OutputCurrent'] = round(random.uniform(420.0, 480.0), 1)
                    payload['Z1_OutputCurrent'] = round(random.uniform(420.0, 480.0), 1)
                    payload['S1_OutputPower'] = round(random.uniform(1.2, 1.8), 6)

                elif elapsed_time <= (phase_duration * 3):
                    # Phase 3 — severe wear: high current, elevated power,
                    # decreasing clamp pressure signals structural stress.
                    payload['X1_OutputCurrent'] = round(random.uniform(650.0, 750.0), 1)
                    payload['Y1_OutputCurrent'] = round(random.uniform(650.0, 750.0), 1)
                    payload['Z1_OutputCurrent'] = round(random.uniform(650.0, 750.0), 1)
                    payload['S1_OutputPower'] = round(random.uniform(2.5, 4.5), 6)
                    payload['clamp_pressure'] = round(random.uniform(0.5, 1.0), 1)

                else:
                    # Phase 4 — failure / worn out: extreme readings
                    # indicate the tool should be replaced immediately.
                    payload['X1_OutputCurrent'] = round(random.uniform(1600.0, 1900.0), 1)
                    payload['Y1_OutputCurrent'] = round(random.uniform(1600.0, 1900.0), 1)
                    payload['Z1_OutputCurrent'] = round(random.uniform(1600.0, 1900.0), 1)
                    payload['S1_OutputPower'] = round(random.uniform(12.5, 15.0), 6)
                    payload['clamp_pressure'] = round(random.uniform(0.01, 0.05), 1)

            if producer:
                try:
                    producer.send(machine_topic, value=payload)
                except Exception as k_err:
                    logger.warning("Kafka send fail for %s: %s", machine_id, k_err)

            local_buffer_trigger = False
            with buffer_lock:
                data_buffer.append(payload)
                if len(data_buffer) >= batch_size:
                    temp_buffer = list(data_buffer)
                    data_buffer = []
                    local_buffer_trigger = True

            if local_buffer_trigger:
                save_to_parquet(temp_buffer)

            logger.info("[%s] -> Generated Live Data.", machine_topic)

            for _ in range(10):
                if stop_event.is_set():
                    break
                time.sleep(0.01)

        except Exception as e:
            logger.error("Error in thread %s: %s", machine_id, e)
            break


if __name__ == "__main__":
    logger.info("Multi-Machine Isolated-Topic Producer Started...")
    logger.info("Target Parquet Path: %s", parquet_file)

    machines = ["CNC_VIRTUAL_01", "CNC_VIRTUAL_02", "CNC_VIRTUAL_03", "CNC_VIRTUAL_04"]
    threads = []

    try:
        for m_id in machines:
            t = threading.Thread(target=machine_worker, args=(m_id,))
            t.daemon = True
            threads.append(t)
            t.start()

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Shutting down safely...")
        stop_event.set()

        # Acquire buffer_lock before reading the shared data_buffer so
        # that no worker thread is mid-append when we snapshot it.
        with buffer_lock:
            remaining = list(data_buffer)
            data_buffer = []

        if remaining:
            logger.info("Saving remaining data before exit...")
            save_to_parquet(remaining)

        # Ensure all buffered Kafka messages are delivered and the
        # producer's network resources are released cleanly.
        if producer:
            try:
                producer.flush()
                producer.close()
                logger.info("Kafka producer flushed and closed.")
            except Exception as e:
                logger.warning("Error closing Kafka producer: %s", e)

        logger.info("Producer stopped successfully.")