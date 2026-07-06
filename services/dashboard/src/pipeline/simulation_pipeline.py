"""
KAVE Intelligent Manufacturing — Simulation Pipeline
======================================================
Handles custom What-If scenario predictions using a pre-trained
XGBoost model. Takes factory resource parameters as input and
predicts the achievable actual productivity.

Author: KAVE Engineering Team
Version: 2.0.0
"""

import os
import joblib
import pandas as pd
from src.pipeline.db_helper import PostgreSQLHelper


class SimulationPipeline:
    """
    Prediction pipeline for What-If factory simulations.
    Loads pre-trained XGBoost model, scaler, label encoders,
    and feature list at initialization.
    """

    def __init__(self):
        """Load all model artifacts from the models/ directory."""
        models_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "models"
        )
        self.model = joblib.load(os.path.join(models_dir, "productivity_rf_model.pkl"))
        self.scaler = joblib.load(os.path.join(models_dir, "feature_scaler.pkl"))
        self.label_encoders = joblib.load(os.path.join(models_dir, "label_encoders.pkl"))
        self.feature_list = joblib.load(os.path.join(models_dir, "feature_list.pkl"))
        self.db = PostgreSQLHelper()
        print("[SimulationPipeline] Model and artifacts loaded successfully.")

    def predict_custom_scenario(
        self, quarter_input, department_input, day_input,
        team_input, target_prod, overtime_input,
        incentive_input, workers_input
    ) -> dict:
        """
        Run a What-If scenario through the XGBoost model.

        Args:
            quarter_input: Season/quarter string (e.g., 'Quarter1').
            department_input: Department name (e.g., 'sewing').
            day_input: Day of week (e.g., 'Monday').
            team_input: Team number (1-12).
            target_prod: Targeted productivity (0.0-1.0).
            overtime_input: Total overtime minutes.
            incentive_input: Incentive budget in USD.
            workers_input: Number of workers.

        Returns:
            dict: {"status": "success", "prediction": float} on success,
                  or {"status": "error", "message": str} on failure.
        """
        try:
            # Encode categorical features
            q_enc = self.label_encoders["quarter"].transform([quarter_input])[0]
            d_enc = self.label_encoders["department"].transform([department_input])[0]
            day_enc = self.label_encoders["day"].transform([day_input])[0]

            # Build feature dictionary with engineered features
            scenario_dict = {
                "quarter": q_enc,
                "department": d_enc,
                "day": day_enc,
                "team": team_input,
                "targeted_productivity": target_prod,
                "smv": 22.0,
                "wip": 500.0,
                "over_time": overtime_input,
                "incentive": incentive_input,
                "no_of_workers": workers_input,
                "idle_time": 0.0,
                "idle_men": 0.0,
                "no_of_style_change": 0.0,
                "month": 2,
                "day_of_month": 15,
                "week_of_year": 7,
                "over_time_per_worker": overtime_input / (workers_input + 1e-5),
                "incentive_per_worker": incentive_input / (workers_input + 1e-5),
                "idle_impact": 0.0,
                "idle_ratio": 0.0,
                "incentive_target_ratio": incentive_input / (target_prod + 1e-5),
                "stress_index": (22.0 * 1) / (workers_input + 1e-5),
            }

            # Predict
            df_pred = pd.DataFrame([scenario_dict])[self.feature_list]
            pred_scaled = self.scaler.transform(df_pred)
            predicted_prod = self.model.predict(pred_scaled)[0]

            # Persist to PostgreSQL
            success, err = self.db.insert_scenario(
                scenario_type="Custom_What_If",
                quarter=quarter_input,
                department=department_input,
                target_prod=target_prod,
                pred_prod=predicted_prod,
                overtime=overtime_input,
                incentive=incentive_input,
                workers=workers_input,
            )

            if success:
                return {"status": "success", "prediction": predicted_prod}
            else:
                return {"status": "error", "message": err}

        except Exception as e:
            return {"status": "error", "message": f"Pipeline Error: {str(e)}"}
