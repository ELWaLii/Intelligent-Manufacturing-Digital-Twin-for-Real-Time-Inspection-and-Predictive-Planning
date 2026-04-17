import json
import pandas as pd
import numpy as np
import joblib
from kafka import KafkaConsumer
from tensorflow.keras.models import load_model
from collections import deque 
import time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# ==========================================
# 0. إعدادات InfluxDB (قم بتعديلها حسب سيرفرك)
# ==========================================
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "t4Zac1hxXZQvIIfeBCoJLJgxJwWIPDPTknBSl54o1erJHqfG3vPdr0RVZocUGIrfSppVa5nF4gXyKbxEnVJRQA==" # ضع التوكن الخاص بك هنا
INFLUX_ORG = "kave_org"                   # اسم المنظمة
INFLUX_BUCKET = "cnc_digital_twin"        # اسم الـ Bucket (قاعدة البيانات)

# الاتصال بـ InfluxDB
client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

print("🛢️ Connected to InfluxDB successfully!")


model = load_model('/home/elwali/Graduation_Project/Intelligent-Manufacturing-Digital-Twin-for-Real-Time-Inspection-and-Predictive-Planning/cnc_lstm_model.keras')
scaler = joblib.load('/home/elwali/Graduation_Project/Intelligent-Manufacturing-Digital-Twin-for-Real-Time-Inspection-and-Predictive-Planning/cnc_scaler.pkl')
features_extracted = joblib.load('/home/elwali/Graduation_Project/Intelligent-Manufacturing-Digital-Twin-for-Real-Time-Inspection-and-Predictive-Planning/model_features.pkl')

print("LSTM Model and Tools loaded successfully. Waiting for live data...")


features_to_use = ['X1_OutputCurrent', 'Y1_OutputCurrent', 'Z1_OutputCurrent', 'S1_OutputPower']
window_size = 10 
seq_length = 10   

buffer_size = window_size + seq_length 
raw_data_buffer = deque(maxlen=buffer_size) 



consumer = KafkaConsumer(
    'cnc_telemetry', 
    bootstrap_servers=['localhost:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)


for message in consumer:
    live_data = message.value 
    

    raw_data_buffer.append(live_data)

    if len(raw_data_buffer) < buffer_size:
        continue
        
    try:
   
        df_buffer = pd.DataFrame(list(raw_data_buffer))
        

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
            # ==========================================
            # 🚀 إرسال البيانات إلى InfluxDB
            # ==========================================
            machine_id = live_data.get('machine_id', 'CNC_VIRTUAL_01')
            
            # إنشاء النقطة (Point) التي سيتم حفظها في الداتابيز
            point = (
                Point("machine_health")
                .tag("machine_id", machine_id)                     # Tags للفلترة
                .tag("process", live_data.get('Machining_Process', 'Unknown'))
                .field("prediction_stage", predicted_stage)        # حالة الأداة (0 إلى 3)
                .field("confidence_percent", confidence)           # نسبة الثقة
                .field("x1_current", float(live_data.get('X1_OutputCurrent', 0))) # تسجيل السنسور لتتبعه
                .field("z1_current", float(live_data.get('Z1_OutputCurrent', 0)))
                .time(time.time_ns(), WritePrecision.NS)           # الوقت اللحظي
            )
            
            # الكتابة في InfluxDB
            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
   
            if predicted_stage == 3:
                print(f"[CRITICAL ALERT] WORN OUT! Stop Machine! Conf: {confidence:.1f}%")
            elif predicted_stage == 2:
                print(f" [WARNING] Severe Wear Detected (Stage 2). Conf: {confidence:.1f}%")
            elif predicted_stage == 1:
                print(f"ℹ [INFO] Initial Wear Started (Stage 1). Conf: {confidence:.1f}%")
            else:
                print(f" Tool is Healthy (Stage 0). Conf: {confidence:.1f}%")
                
    except Exception as e:
        print(f"Error processing live stream: {e}")