import os
import pandas as pd
import numpy as np
import joblib
from sklearn.preprocessing import LabelEncoder

class DataTransformation:
    def __init__(self):
        self.processed_data_path = os.path.join('data', 'processed.csv')
        self.features_to_keep = [
            'quarter', 'department', 'day', 'team', 'targeted_productivity',
            'smv', 'wip', 'over_time', 'incentive', 'idle_time', 'idle_men', 
            'no_of_style_change', 'no_of_workers', 'month', 'day_of_month', 
            'week_of_year', 'over_time_per_worker', 'incentive_per_worker', 
            'idle_impact', 'idle_ratio', 
            'incentive_target_ratio', 'stress_index' 
        ]

    def initiate_data_transformation(self, raw_path):
        print(" [Data Transformation] Advanced Feature Engineering for High Accuracy...")
        df = pd.read_csv(raw_path)
        
        df['department'] = df['department'].str.strip()
        df['department'] = df['department'].replace({'sweing': 'sewing'})
        df['wip'] = df['wip'].fillna(0)
        
        q_incentive = df['incentive'].quantile(0.99)
        df = df[df['incentive'] < q_incentive]
        
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.month
        df['day_of_month'] = df['date'].dt.day
        df['week_of_year'] = df['date'].dt.isocalendar().week.astype(int)
        
        df['over_time_per_worker'] = df['over_time'] / (df['no_of_workers'] + 1e-5)
        df['incentive_per_worker'] = df['incentive'] / (df['no_of_workers'] + 1e-5)
        df['idle_impact'] = df['idle_time'] * df['idle_men']
        df['idle_ratio'] = df['idle_time'] / (df['smv'] + 1e-5)
        
        df['incentive_target_ratio'] = df['incentive'] / (df['targeted_productivity'] + 1e-5)
        df['stress_index'] = (df['smv'] * (df['no_of_style_change'] + 1)) / (df['no_of_workers'] + 1e-5)
        
        target = df['actual_productivity']
        
        # 6. الـ Label Encoding
        label_encoders = {}
        categorical_cols = ['quarter', 'department', 'day']
        for col in categorical_cols:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col])
            label_encoders[col] = le
            
        X_transformed = df[self.features_to_keep].copy()
        processed_df = X_transformed.copy()
        processed_df['actual_productivity'] = target
        
        os.makedirs('models', exist_ok=True)
        joblib.dump(label_encoders, os.path.join('models', 'label_encoders.pkl'))
        joblib.dump(self.features_to_keep, os.path.join('models', 'feature_list.pkl'))
        
        processed_df.to_csv(self.processed_data_path, index=False)
        print(f"[Data Transformation] Enhanced dataset saved. Total rows: {len(processed_df)}")
        return self.processed_data_path

if __name__ == "__main__":
    transformer = DataTransformation()
    transformer.initiate_data_transformation(os.path.join('data', 'raw.csv'))