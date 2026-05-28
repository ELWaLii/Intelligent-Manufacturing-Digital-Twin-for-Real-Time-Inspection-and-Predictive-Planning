import numpy as np
import pandas as pd
import json
import time
import random
import os
import threading
from kafka import KafkaProducer
import pyarrow as pa
import pyarrow.parquet as pq

try:
    producer = KafkaProducer(
        bootstrap_servers=['127.0.0.1:9092'],
        value_serializer=lambda x: json.dumps(x).encode('utf-8'),
        max_block_ms=2000 
    )
    print("Kafka Producer initialized successfully.")
except Exception as e:
    print(f"Kafka Initialization Error: {e}")
    producer = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
parquet_file = os.path.join(BASE_DIR, 'cnc_historical_data.parquet')

batch_size = 10  
data_buffer = []
buffer_lock = threading.Lock()

sensor_ranges = {
    'X1': {'pos': (141.0, 198.0), 'vel': (-20.4, 50.7), 'acc': (-1280, 1440), 'volt': (320, 331)},
    'Y1': {'pos': (72.4, 158.0), 'vel': (-32.8, 50.4), 'acc': (-1260, 1460), 'volt': (319, 333)},
    'Z1': {'pos': (27.5, 119.0), 'vel': (-51.5, 50.9), 'acc': (-1260, 1270), 'volt': (0, 0)},
    'S1': {'pos': (-2150, 2150), 'vel': (-0.06, 53.8), 'acc': (-150, 150), 'pwr': (0, 0.56)}
}

machine_profiles = {
    "CNC_VIRTUAL_01": 1.0,   
    "CNC_VIRTUAL_02": 1.0,   
    "CNC_VIRTUAL_03": 1.35, 
    "CNC_VIRTUAL_04": 0.75  
}

def generate_row(machine_id):
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
    if not buffer_to_save:
        return
    try:
        df_batch = pd.DataFrame(list(buffer_to_save))
        table = pa.Table.from_pandas(df_batch)
        
        with buffer_lock:
            if not os.path.isfile(parquet_file):
                pq.write_table(table, parquet_file, compression='snappy')
            else:
                with pq.ParquetWriter(parquet_file, table.schema, compression='snappy') as writer:
                    writer.write_table(table)
                
        print(f"[SUCCESS] Parquet file updated successfully at: {parquet_file}")
    except Exception as e:
        print(f"HARD DISK WRITE ERROR: {e}")

def machine_worker(machine_id):
    global data_buffer
    print(f"Worker for {machine_id} started...")
    machine_topic = f"cnc_telemetry_{machine_id}"
    
    start_time = time.time()
    
    phase_duration = 5 
    
    while not stop_event.is_set():
        try:
            payload = generate_row(machine_id)
            
            if machine_id == "CNC_VIRTUAL_02":
                elapsed_time = time.time() - start_time
                
                if elapsed_time <= phase_duration:
                    pass 
                    
                elif elapsed_time <= (phase_duration * 2):
                    payload['X1_OutputCurrent'] = round(random.uniform(420.0, 480.0), 1)
                    payload['Y1_OutputCurrent'] = round(random.uniform(420.0, 480.0), 1)
                    payload['Z1_OutputCurrent'] = round(random.uniform(420.0, 480.0), 1)
                    payload['S1_OutputPower'] = round(random.uniform(1.2, 1.8), 6)
                    
                elif elapsed_time <= (phase_duration * 3):
                    payload['X1_OutputCurrent'] = round(random.uniform(650.0, 750.0), 1)
                    payload['Y1_OutputCurrent'] = round(random.uniform(650.0, 750.0), 1)
                    payload['Z1_OutputCurrent'] = round(random.uniform(650.0, 750.0), 1)
                    payload['S1_OutputPower'] = round(random.uniform(2.5, 4.5), 6)
                    payload['clamp_pressure'] = round(random.uniform(0.5, 1.0), 1)
                    
                else:
                    payload['X1_OutputCurrent'] = round(random.uniform(1600.0, 1900.0), 1)
                    payload['Y1_OutputCurrent'] = round(random.uniform(1600.0, 1900.0), 1)
                    payload['Z1_OutputCurrent'] = round(random.uniform(1600.0, 1900.0), 1)
                    payload['S1_OutputPower'] = round(random.uniform(12.5, 15.0), 6)
                    payload['clamp_pressure'] = round(random.uniform(0.01, 0.05), 1)

            if producer:
                try:
                    producer.send(machine_topic, value=payload)
                except Exception as k_err:
                    print(f"Kafka send fail for {machine_id}: {k_err}")
            
            local_buffer_trigger = False
            with buffer_lock:
                data_buffer.append(payload)
                if len(data_buffer) >= batch_size:
                    temp_buffer = list(data_buffer)
                    data_buffer = []
                    local_buffer_trigger = True
            
            if local_buffer_trigger:
                save_to_parquet(temp_buffer)
                    
            print(f"[{machine_topic}] -> Generated Live Data.")
            
            for _ in range(10):
                if stop_event.is_set():
                    break
                time.sleep(0.01)
                
        except Exception as e:
            print(f"Error in thread {machine_id}: {e}")
            break

if __name__ == "__main__":
    print("Multi-Machine Isolated-Topic Producer Started...")
    print(f"Target Parquet Path: {parquet_file}")
    
    machines = ["CNC_VIRTUAL_01", "CNC_VIRTUAL_02", "CNC_VIRTUAL_03", "CNC_VIRTUAL_04"]
    threads = []
    stop_event = threading.Event()

    try:
        for m_id in machines:
            t = threading.Thread(target=machine_worker, args=(m_id,))
            t.daemon = True 
            threads.append(t)
            t.start()

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nShutting down safely...")
        stop_event.set()
        
        if data_buffer:
            print("Saving remaining data before exit...")
            save_to_parquet(data_buffer)
            
        print("Producer stopped successfully.")