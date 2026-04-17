import numpy as np
import pandas as pd
import json
import time
import random
import os
from kafka import KafkaProducer

#Kafka
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)

# Parquet
parquet_file = 'cnc_historical_data.parquet'
batch_size = 100  
data_buffer = []

sensor_ranges = {
    'X1': {'pos': (141.0, 198.0), 'vel': (-20.4, 50.7), 'acc': (-1280, 1440), 'volt': (320, 331)},
    'Y1': {'pos': (72.4, 158.0), 'vel': (-32.8, 50.4), 'acc': (-1260, 1460), 'volt': (319, 333)},
    'Z1': {'pos': (27.5, 119.0), 'vel': (-51.5, 50.9), 'acc': (-1260, 1270), 'volt': (0, 0)},
    'S1': {'pos': (-2150, 2150), 'vel': (-0.06, 53.8), 'acc': (-150, 150), 'pwr': (0, 0.56)}
}

def generate_row():
    data = {}
    for axis in ['X1', 'Y1', 'Z1', 'S1']:
        base_pos = random.uniform(*sensor_ranges[axis]['pos'])
        data[f'{axis}_ActualPosition'] = round(base_pos, 3)
        data[f'{axis}_CommandPosition'] = round(base_pos + random.uniform(-0.05, 0.05), 3)
        data[f'{axis}_ActualVelocity'] = round(random.uniform(*sensor_ranges[axis]['vel']), 3)
        data[f'{axis}_CommandVelocity'] = round(data[f'{axis}_ActualVelocity'] + random.uniform(-0.1, 0.1), 3)
        data[f'{axis}_ActualAcceleration'] = round(random.uniform(*sensor_ranges[axis]['acc']), 2)
        data[f'{axis}_CommandAcceleration'] = round(data[f'{axis}_ActualAcceleration'] + 1.0, 2)
        data[f'{axis}_CurrentFeedback'] = round(random.uniform(-5, 30), 3)
        data[f'{axis}_DCBusVoltage'] = round(random.uniform(0, 0.4), 4)
        data[f'{axis}_OutputCurrent'] = round(random.uniform(320, 330), 1)
        data[f'{axis}_OutputVoltage'] = round(random.uniform(0, 80), 2)
        if 'pwr' in sensor_ranges[axis]:
            data[f'{axis}_OutputPower'] = round(random.uniform(*sensor_ranges[axis]['pwr']), 6)

    data['M1_CURRENT_PROGRAM_NUMBER'] = 1.0
    data['M1_sequence_number'] = float(random.randint(1, 150))
    data['M1_CURRENT_FEEDRATE'] = float(random.choice([3, 6, 20, 50]))
    data['Machining_Process'] = random.choice(['Starting', 'Prep', 'Layer_Processing', 'Finalizing'])
    data['feedrate'] = data['M1_CURRENT_FEEDRATE']
    data['clamp_pressure'] = round(random.uniform(2.5, 4.0), 1)
    data['machine_id'] = "CNC_VIRTUAL_01"
    data['event_timestamp'] = time.time()
    return data

def save_to_parquet(buffer):
    df_batch = pd.DataFrame(buffer)
    
    if not os.path.isfile(parquet_file):
        df_batch.to_parquet(parquet_file, engine='fastparquet')
    else:
        df_batch.to_parquet(parquet_file, engine='fastparquet', append=True)
    print(f" Successfully saved {len(buffer)} records to Parquet file.")


print(" Dual-Stream Producer Started (Kafka + Parquet)...")
try:
    while True:
        payload = generate_row()
        
        
        producer.send('cnc_telemetry', value=payload)
        
        
        data_buffer.append(payload)
        
        
        if len(data_buffer) >= batch_size:
            save_to_parquet(data_buffer)
            data_buffer = [] 
        
        time.sleep(0.05) 

except KeyboardInterrupt:
    if data_buffer: 
        save_to_parquet(data_buffer)
    print(" Producer stopped.")
