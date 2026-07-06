"""
KAVE — Data Ingestion Component
Loads raw production data from CSV for the ML pipeline.
"""

import os
import pandas as pd


class DataIngestion:
    """Handles loading and validation of raw production data."""

    def __init__(self):
        """Set the raw data path relative to the project root."""
        self_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(self_dir))
        self.raw_data_path = os.path.join(project_root, "data", "raw.csv")

    def initiate_data_ingestion(self) -> str:
        """
        Validate and load the raw data file.

        Returns:
            str: Path to the raw data file.

        Raises:
            FileNotFoundError: If the raw data file is missing.
        """
        print(f"[Data Ingestion] Checking for raw data at: {self.raw_data_path}")
        if not os.path.exists(self.raw_data_path):
            raise FileNotFoundError(
                f"Raw data file not found at: {self.raw_data_path}. "
                "Please check your directory structure."
            )

        df = pd.read_csv(self.raw_data_path)
        print(f"[Data Ingestion] Raw data loaded. Shape: {df.shape}")
        return self.raw_data_path


if __name__ == "__main__":
    try:
        ingestion = DataIngestion()
        ingestion.initiate_data_ingestion()
    except Exception as e:
        print(f"Ingestion Test Failed: {e}")
