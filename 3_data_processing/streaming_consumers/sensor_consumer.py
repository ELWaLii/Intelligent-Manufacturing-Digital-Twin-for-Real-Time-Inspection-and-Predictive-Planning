import json
import pandas as pd
import numpy as np
import joblib
from kafka import KafkaConsumer
from tensorflow.keras.models import load_model
from collections import deque 


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
            predicted_stage = np.argmax(probabilities) 
            confidence = probabilities[predicted_stage] * 100
            
   
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