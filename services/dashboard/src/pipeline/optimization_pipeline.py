"""
KAVE Intelligent Manufacturing — Optimization Pipeline
========================================================
AI-powered Seasonal Operations Optimizer that uses Grid Search
to find the most cost-effective shift configuration meeting a
given productivity target. Results are persisted to PostgreSQL.

Author: KAVE Engineering Team
Version: 2.0.0
"""

import os
import joblib
import pandas as pd
from itertools import product
from src.pipeline.db_helper import PostgreSQLHelper


class OptimizationPipeline:
    """
    Grid-search optimizer for seasonal shift planning.
    Scans combinations of workers, overtime, and incentives to find
    the cheapest plan that meets the target productivity.
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
        print("[OptimizationPipeline] Model and artifacts loaded successfully.")

    def find_best_seasonal_plan(
        self, quarter_input: str, department_input: str, target_prod: float
    ) -> dict:
        """
        Find the most cost-effective plan that achieves the target productivity.

        Uses Grid Search across combinations of:
          - Workers: [20, 30, 40, 50, 60]
          - Overtime: [0, 1000, 3000, 5000]
          - Incentives: [0, 30, 60, 100]

        Cost function: (workers × $50) + (overtime × $0.10) + incentive

        Args:
            quarter_input: Target season/quarter.
            department_input: Target department.
            target_prod: Minimum required productivity (0.0-1.0).

        Returns:
            dict: {"status": "success", "plan": {...}} on success,
                  or {"status": "error", "message": str} on failure.
        """
        try:
            # Encode categorical features
            q_enc = self.label_encoders["quarter"].transform([quarter_input])[0]
            d_enc = self.label_encoders["department"].transform([department_input])[0]
            day_enc = self.label_encoders["day"].transform(["Wednesday"])[0]

            # Grid search space
            workers_opts = [20, 30, 40, 50, 60]
            overtime_opts = [0, 1000, 3000, 5000]
            incentive_opts = [0, 30, 60, 100]

            best_plan = None
            min_cost = float("inf")
            absolute_best_pred = 0
            fallback_plan = None

            for w, ot, inc in product(workers_opts, overtime_opts, incentive_opts):
                scenario_dict = {
                    "quarter": q_enc,
                    "department": d_enc,
                    "day": day_enc,
                    "team": 1,
                    "targeted_productivity": target_prod,
                    "smv": 22.0,
                    "wip": 500.0,
                    "over_time": ot,
                    "incentive": inc,
                    "no_of_workers": w,
                    "idle_time": 0.0,
                    "idle_men": 0.0,
                    "no_of_style_change": 0.0,
                    "month": 2,
                    "day_of_month": 15,
                    "week_of_year": 7,
                    "over_time_per_worker": ot / (w + 1e-5),
                    "incentive_per_worker": inc / (w + 1e-5),
                    "idle_impact": 0.0,
                    "idle_ratio": 0.0,
                    "incentive_target_ratio": inc / (target_prod + 1e-5),
                    "stress_index": (22.0 * 1) / (w + 1e-5),
                }

                df_pred = pd.DataFrame([scenario_dict])[self.feature_list]
                pred_scaled = self.scaler.transform(df_pred)
                pred = self.model.predict(pred_scaled)[0]

                # Track absolute best in case no plan meets the target
                if pred > absolute_best_pred:
                    absolute_best_pred = pred
                    fallback_plan = {
                        "strategy": "Best Achievable Strategy (Sub-optimal)",
                        "no_of_workers": w,
                        "over_time": ot,
                        "incentive": inc,
                        "predicted_productivity": float(pred),
                    }

                # Check if this plan meets the target at minimum cost
                if pred >= target_prod:
                    cost = (w * 50) + (ot * 0.1) + inc
                    if cost < min_cost:
                        min_cost = cost
                        best_plan = {
                            "strategy": "Cost-Optimized Target Match",
                            "no_of_workers": w,
                            "over_time": ot,
                            "incentive": inc,
                            "predicted_productivity": float(pred),
                        }

            # Use fallback if no plan met the exact target
            if not best_plan:
                best_plan = fallback_plan

            # Persist the golden plan to PostgreSQL
            if best_plan:
                self.db.insert_scenario(
                    scenario_type="Golden_Plan",
                    quarter=quarter_input,
                    department=department_input,
                    target_prod=target_prod,
                    pred_prod=best_plan["predicted_productivity"],
                    overtime=best_plan["over_time"],
                    incentive=best_plan["incentive"],
                    workers=best_plan["no_of_workers"],
                )

            return {"status": "success", "plan": best_plan}

        except Exception as e:
            return {"status": "error", "message": f"Optimization Error: {str(e)}"}
