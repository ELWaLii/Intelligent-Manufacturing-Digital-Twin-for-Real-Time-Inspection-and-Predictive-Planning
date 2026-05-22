import os
import pandas as pd
import sys

class DataIngestion:
    def __init__(self):
        
        SELF_DIR = os.path.dirname(os.path.abspath(__file__)) 
        PROJECT_ROOT = os.path.dirname(os.path.dirname(SELF_DIR)) 
        self.raw_data_path = os.path.join(PROJECT_ROOT, 'data', 'raw.csv')

    def initiate_data_ingestion(self):
        print(f" [Data Ingestion] Dynamic check for raw data at: {self.raw_data_path}")
        if not os.path.exists(self.raw_data_path):
            raise FileNotFoundError(
                f" Base raw file not found at calculated path: {self.raw_data_path}. "
                "Please check your directory structure and try again."
            )
        
        df = pd.read_csv(self.raw_data_path)
        print(f" [Data Ingestion] Raw data loaded. Shape: {df.shape}")
        return self.raw_data_path

if __name__ == "__main__":
   
    try:
        ingestion = DataIngestion()
        ingestion.initiate_data_ingestion()
    except Exception as e:
        print(f" Ingestion Test Failed: {e}")