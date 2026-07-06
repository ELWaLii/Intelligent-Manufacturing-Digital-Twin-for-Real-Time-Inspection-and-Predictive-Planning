"""KAVE CNC Digital Twin — IoT Sensor Data Preprocessing & LSTM Training.

This module processes raw historical CNC sensor data, engineers rolling-window
features (standard deviation and RMS), and clusters the data into wear stages
using KMeans. It then trains an LSTM neural network to predict the wear stage
from sequences of sensor readings.

The output artifacts (LSTM model, scaler, KMeans model, and feature list)
are saved for real-time use by the streaming consumer.

Usage:
    python IOT_Data_Preprocessing.py
"""

import os
import logging
import pandas as pd
import numpy as np
import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("kave.preprocessing")


def create_sequences(data, labels, seq_length):
    """Create time-series sequences from flattened data for LSTM training.

    Args:
        data (np.ndarray): The scaled feature matrix.
        labels (np.ndarray): The corresponding integer labels (wear stages).
        seq_length (int): The number of consecutive timesteps in each sequence.

    Returns:
        tuple: (X_time_series, y_wear_stages)
            - X_time_series (np.ndarray): 3D tensor of shape (samples, seq_length, features).
            - y_wear_stages (np.ndarray): 1D array of target labels.
    """
    xs, ys = [], []
    for i in range(len(data) - seq_length):
        x = data[i:(i + seq_length)]
        y = labels[i + seq_length]
        xs.append(x)
        ys.append(y)
    return np.array(xs), np.array(ys, dtype=np.int32)


def main():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(BASE_DIR, "..", "..", "datasets", "raw_sensor_data", "Cleaned_MergedData.csv")

    logger.info("Reading data file from: %s", csv_path)
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        logger.error("Failed to read CSV at %s: %s", csv_path, e)
        return

    cutting_stages = ['Layer 1 Up', 'Layer 1 Down', 'Layer 2 Up', 'Layer 2 Down', 'Layer 3 Up', 'Layer 3 Down']
    df_cutting = df[df['Machining_Process'].isin(cutting_stages)].copy()

    features_to_use = ['X1_OutputCurrent', 'Y1_OutputCurrent', 'Z1_OutputCurrent', 'S1_OutputPower']

    logger.info("Calculating statistical indicators (Rolling STD & RMS)...")
    window_size = 10
    for col in features_to_use:
        df_cutting[f'{col}_std'] = df_cutting[col].rolling(window=window_size).std()
        df_cutting[f'{col}_rms'] = np.sqrt((df_cutting[col]**2).rolling(window=window_size).mean())

    df_cutting.dropna(inplace=True)

    features_extracted = [col for col in df_cutting.columns if '_std' in col or '_rms' in col]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_cutting[features_extracted])

    logger.info("Running KMeans to determine wear stages...")
    num_wear_stages = 4
    kmeans = KMeans(n_clusters=num_wear_stages, random_state=42, n_init=10)
    raw_wear_stages = kmeans.fit_predict(X_scaled)

    logger.info("Reordering wear stages chronologically (0 Safe -> 3 Failure)...")
    # Chronological Reordering Logic:
    # KMeans assigns cluster IDs arbitrarily. Assuming wear happens progressively over time,
    # we calculate the mean original dataframe index for each cluster.
    # Clusters with a lower mean index occurred earlier in the dataset (i.e. healthier state).
    # We sort the clusters by their mean index so that 0 is the earliest stage and 3 is the latest.
    idx_means = []
    for i in range(num_wear_stages):
        matching_indices = df_cutting.index[raw_wear_stages == i].values
        if len(matching_indices) > 0:
            idx_means.append(matching_indices.mean())
        else:
            idx_means.append(0.0)

    ordered_stages = np.argsort(idx_means)
    mapping = {ordered_stages[i]: i for i in range(num_wear_stages)}

    wear_stages = np.array([mapping[stage] for stage in raw_wear_stages])
    df_cutting['Wear_Stage'] = wear_stages

    logger.info("\nFinal wear stage distribution after reordering:\n%s", df_cutting['Wear_Stage'].value_counts().sort_index())

    seq_length = 10  
    X_time_series, y_wear_stages = create_sequences(X_scaled, wear_stages, seq_length)

    indices = np.arange(X_time_series.shape[0])
    np.random.seed(42) 
    np.random.shuffle(indices)

    X_time_series = X_time_series[indices]
    y_wear_stages = y_wear_stages[indices]

    logger.info("LSTM data dimensions after shuffling: %s", X_time_series.shape)

    model_lstm = Sequential()
    model_lstm.add(LSTM(64, return_sequences=False, input_shape=(seq_length, len(features_extracted))))
    model_lstm.add(Dropout(0.3)) 
    model_lstm.add(Dense(num_wear_stages, activation='softmax')) 

    model_lstm.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])

    logger.info("Training the LSTM model...")
    model_lstm.fit(X_time_series, y_wear_stages, epochs=15, batch_size=32, validation_split=0.2)

    logger.info("Saving all artifacts and the model...")
    try:
        model_lstm.save(os.path.join(BASE_DIR, 'cnc_lstm_model.keras')) 
        joblib.dump(scaler, os.path.join(BASE_DIR, 'cnc_scaler.pkl'))
        joblib.dump(kmeans, os.path.join(BASE_DIR, 'cnc_kmeans.pkl'))
        joblib.dump(features_extracted, os.path.join(BASE_DIR, 'model_features.pkl'))
        logger.info("Process completed successfully! Files are ready for the consumer.")
    except Exception as e:
        logger.error("Failed to save artifacts: %s", e)


if __name__ == "__main__":
    main()