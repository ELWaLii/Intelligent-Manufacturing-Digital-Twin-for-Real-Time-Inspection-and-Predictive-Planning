import os
import joblib
import pandas as pd
from itertools import product

class OptimizationPipeline:
    def __init__(self):
        self.model = joblib.load(os.path.join('models', 'productivity_rf_model.pkl'))
        self.scaler = joblib.load(os.path.join('models', 'feature_scaler.pkl'))
        self.label_encoders = joblib.load(os.path.join('models', 'label_encoders.pkl'))
        self.feature_list = joblib.load(os.path.join('models', 'feature_list.pkl'))

    def find_best_seasonal_plan(self, quarter_input, department_input, target_prod):
        try:
            q_enc = self.label_encoders['quarter'].transform([quarter_input])[0]
            d_enc = self.label_encoders['department'].transform([department_input])[0]
            day_enc = self.label_encoders['day'].transform(['Wednesday'])[0] 
            
            workers_opts = [20, 30, 40, 50, 60]
            overtime_opts = [0, 1000, 3000, 5000]
            incentive_opts = [0, 30, 60, 100]

            best_plan = None
            min_cost = float('inf')
            
            absolute_best_pred = 0
            fallback_plan = None

            for w, ot, inc in product(workers_opts, overtime_opts, incentive_opts):
                scenario_dict = {
                    'quarter': q_enc, 'department': d_enc, 'day': day_enc, 'team': 1,
                    'targeted_productivity': target_prod, 'smv': 22.0, 'wip': 500.0, 'over_time': ot,
                    'incentive': inc, 'no_of_workers': w,
                    'idle_time': 0.0, 'idle_men': 0.0, 'no_of_style_change': 0.0,
                    'month': 2, 'day_of_month': 15, 'week_of_year': 7,
                    'over_time_per_worker': ot / (w + 1e-5),
                    'incentive_per_worker': inc / (w + 1e-5),
                    'idle_impact': 0.0, 'idle_ratio': 0.0,
                    'incentive_target_ratio': inc / (target_prod + 1e-5),
                    'stress_index': (22.0 * 1) / (w + 1e-5)
                }

                df_pred = pd.DataFrame([scenario_dict])[self.feature_list]
                pred_scaled = self.scaler.transform(df_pred)
                pred = self.model.predict(pred_scaled)[0]

                if pred > absolute_best_pred:
                    absolute_best_pred = pred
                    fallback_plan = {
                        'strategy': "Best Achievable Strategy (Sub-optimal)",
                        'no_of_workers': w,
                        'over_time': ot,
                        'incentive': inc,
                        'predicted_productivity': float(pred)
                    }

                if pred >= target_prod:
                    cost = (w * 50) + (ot * 0.1) + inc
                    if cost < min_cost:
                        min_cost = cost
                        best_plan = {
                            'strategy': "Cost-Optimized Target Match",
                            'no_of_workers': w,
                            'over_time': ot,
                            'incentive': inc,
                            'predicted_productivity': float(pred)
                        }

            if not best_plan:
                best_plan = fallback_plan

            return {"status": "success", "plan": best_plan}

        except Exception as e:
            return {"status": "error", "message": f"Optimization Error: {str(e)}"}