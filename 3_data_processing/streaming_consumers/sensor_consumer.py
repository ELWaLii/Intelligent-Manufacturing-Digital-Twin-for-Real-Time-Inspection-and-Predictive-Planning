import json
import os
import time
import threading
from collections import deque
import numpy as np
import pandas as pd
import joblib
from kafka import KafkaConsumer
from tensorflow.keras.models import load_model
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS


INFLUX_URL = "http://127.0.0.1:8089" 
INFLUX_TOKEN = "t4Zac1hxXZQvIIfeBCoJLJgxJwWIPDPTknBSl54o1erJHqfG3vPdr0RVZocUGIrfSppVa5nF4gXyKbxEnVJRQA==" 
INFLUX_ORG = "kave_org"                  
INFLUX_BUCKET = "cnc_digital_twin"        

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

db_write_lock = threading.Lock()

print("Connected to InfluxDB successfully on Port 8089!")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

model_path = os.path.join(BASE_DIR, 'cnc_lstm_model.keras')
scaler_path = os.path.join(BASE_DIR, 'cnc_scaler.pkl')
features_path = os.path.join(BASE_DIR, 'model_features.pkl')

print("Loading model and training tools from the current directory...")

model = load_model(model_path)
scaler = joblib.load(scaler_path)
features_extracted = joblib.load(features_path)

print("LSTM Model and Tools loaded successfully. Waiting for live data...")

features_to_use = ['X1_OutputCurrent', 'Y1_OutputCurrent', 'Z1_OutputCurrent', 'S1_OutputPower']
window_size = 10 
seq_length = 10   
buffer_size = window_size + seq_length 

buffer_lock = threading.Lock()
machine_buffers = {} 

def machine_consumer_worker(machine_id):
    topic_name = f"cnc_telemetry_{machine_id}"
    print(f" Thread started and listening to: {topic_name}")
    
    consumer = KafkaConsumer(
        topic_name,
        bootstrap_servers=['127.0.0.1:9092'],
        auto_offset_reset='latest', 
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    
    for message in consumer:
        try:
            live_data = message.value
            
            with buffer_lock:
                if machine_id not in machine_buffers:
                    machine_buffers[machine_id] = deque(maxlen=buffer_size)
                machine_buffers[machine_id].append(live_data)
                current_len = len(machine_buffers[machine_id])
                local_buffer_snapshot = list(machine_buffers[machine_id])
            
            print(f"[{topic_name}] -> Received data | Buffer status: ({current_len}/{buffer_size})")

            if current_len < buffer_size:
                continue
                
            df_buffer = pd.DataFrame(local_buffer_snapshot)
            
            for col in features_to_use:
                if col in df_buffer.columns:
                    df_buffer[f'{col}_std'] = df_buffer[col].rolling(window=window_size).std()
                    df_buffer[f'{col}_rms'] = np.sqrt((df_buffer[col]**2).rolling(window=window_size).mean())
            
            df_features = df_buffer.dropna().copy()
            
            if len(df_features) >= seq_length:
                df_seq = df_features[features_extracted].tail(seq_length)
                seq_scaled = scaler.transform(df_seq)
                X_live = seq_scaled.reshape(1, seq_length, len(features_extracted))
                
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
                    print(f" CRITICAL: {machine_id} WORN OUT! Stop Machine! Confidence: {confidence:.1f}%")
                elif predicted_stage == 2:
                    print(f" WARNING: {machine_id} Severe Wear Detected. Confidence: {confidence:.1f}%")
                elif predicted_stage == 1:
                    print(f" INFO: {machine_id} Initial Wear Started. Confidence: {confidence:.1f}%")
                else:
                    print(f" OK: {machine_id} Tool is Healthy. Confidence: {confidence:.1f}%")
                    
        except Exception as e:
            print(f" ERROR in Thread {machine_id} during live processing: {e}")

if __name__ == "__main__":
    machines_list = ['CNC_VIRTUAL_01', 'CNC_VIRTUAL_02', 'CNC_VIRTUAL_03', 'CNC_VIRTUAL_04']
    active_threads = []
    
    print("\nStarting Parallel Real-Time Consumers Pipeline...")
    
    for m_id in machines_list:
        thread = threading.Thread(target=machine_consumer_worker, args=(m_id,))
        thread.daemon = True
        active_threads.append(thread)
        thread.start()
        time.sleep(0.2) 

    print("All parallel consumers are online and listening! Press Ctrl+C to exit.\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n Stopping Parallel Consumers Pipeline... Done.")