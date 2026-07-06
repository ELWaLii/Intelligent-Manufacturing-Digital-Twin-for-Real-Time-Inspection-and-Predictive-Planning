"""
KAVE — Model Trainer Component
Trains an XGBoost regressor for garment productivity prediction.
"""

import os
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, r2_score


class ModelTrainer:
    """XGBoost model training pipeline with hyperparameter tuning."""

    def __init__(self):
        """Initialize model paths and XGBoost configuration."""
        self.trained_model_path = os.path.join("models", "productivity_rf_model.pkl")
        self.scaler_path = os.path.join("models", "feature_scaler.pkl")

        self.model = XGBRegressor(
            n_estimators=500,
            max_depth=5,
            learning_rate=0.03,
            subsample=0.7,
            colsample_bytree=0.9,
            reg_alpha=0.1,
            reg_lambda=1.5,
            random_state=42,
            n_jobs=-1,
        )
        self.scaler = StandardScaler()

    def initiate_model_trainer(self, processed_path: str):
        """
        Train the XGBoost model on processed data.

        Args:
            processed_path: Path to the processed CSV file.
        """
        df = pd.read_csv(processed_path)

        X = df.drop(columns=["actual_productivity"])
        y = df["actual_productivity"]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.15, random_state=42
        )

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        print("[Model Trainer] Training XGBoost with optimized hyperparameters...")
        self.model.fit(
            X_train_scaled, y_train,
            eval_set=[(X_test_scaled, y_test)],
            verbose=False,
        )

        predictions = self.model.predict(X_test_scaled)
        mae = mean_absolute_error(y_test, predictions)
        r2 = r2_score(y_test, predictions)

        print("=" * 55)
        print(" OPTIMIZED XGBoost PERFORMANCE METRICS ")
        print("=" * 55)
        print(f"  Mean Absolute Error (MAE): {mae:.4f} (loss {mae * 100:.1f}%)")
        print(f"  R2 Score (Accuracy)      : {r2 * 100:.2f}%")
        print("=" * 55)

        joblib.dump(self.model, self.trained_model_path)
        joblib.dump(self.scaler, self.scaler_path)
        print("[Model Trainer] Model saved successfully!")


if __name__ == "__main__":
    trainer = ModelTrainer()
    trainer.initiate_model_trainer(os.path.join("data", "processed.csv"))
