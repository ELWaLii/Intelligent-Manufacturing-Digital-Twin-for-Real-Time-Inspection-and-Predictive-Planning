import os
import sys
import pandas as pd
import numpy as np
import joblib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.pipeline.db_helper import PostgreSQLHelper

class OptimizationPipeline:
    def __init__(self):
        self.model = joblib.load(os.path.join('models', 'productivity_rf_model.pkl'))
        self.scaler = joblib.load(os.path.join('models', 'feature_scaler.pkl'))
        self.label_encoders = joblib.load(os.path.join('models', 'label_encoders.pkl'))
        self.feature_list = joblib.load(os.path.join('models', 'feature_list.pkl'))
        self.db = PostgreSQLHelper()

    def find_best_seasonal_plan(self, quarter_input, department_input, target_prod):
        q_encoded = self.label_encoders['quarter'].transform([quarter_input])[0]
        d_encoded = self.label_encoders['department'].transform([department_input])[0]
        day_default = self.label_encoders['day'].transform(['Monday'])[0]
        
        possible_overtime = [0, 1440, 3000, 6000]  
        possible_incentives = [0, 20, 45, 75]      
        possible_workers = [10, 30, 55]             
        
        scenarios_list = []
        configs_list = []
        
        for ot in possible_overtime:
            for inc in possible_incentives:
                for wrk in possible_workers:
                    ot_per_worker = ot / (wrk + 1e-5)
                    inc_per_worker = inc / (wrk + 1e-5)
                    
                    inc_target_ratio = inc / (target_prod + 1e-5)
                    stress_idx = (22.0 * (0.0 + 1)) / (wrk + 1e-5)
                    
                    scenarios_list.append({
                        'quarter': q_encoded, 'department': d_encoded, 'day': day_default, 'team': 1,
                        'targeted_productivity': target_prod, 'smv': 22.0, 'wip': 500.0, 'over_time': ot,
                        'incentive': inc, 'idle_time': 0.0, 'idle_men': 0.0, 'no_of_style_change': 0.0,
                        'no_of_workers': wrk, 'month': 2, 'day_of_month': 15, 'week_of_year': 7,
                        'over_time_per_worker': ot_per_worker, 'incentive_per_worker': inc_per_worker,
                        'idle_impact': 0.0, 'idle_ratio': 0.0,
                        'incentive_target_ratio': inc_target_ratio,  
                        'stress_index': stress_idx                   
                    })
                    configs_list.append({'over_time': ot, 'incentive': inc, 'no_of_workers': wrk})
                    
        df_grid = pd.DataFrame(scenarios_list)[self.feature_list]
        df_grid_scaled = self.scaler.transform(df_grid)
        
        predictions = self.model.predict(df_grid_scaled)
        
        best_idx = np.argmax(predictions)
        best_prod = predictions[best_idx]
        best_plan = configs_list[best_idx]
        
        if best_plan['over_time'] == 0:
            strategy = "Standard Single Shift"
        elif best_plan['over_time'] < 4000:
            strategy = "Extended Shift (Overtime Included)"
        else:
            strategy = "Double Shift (Two balanced shifts)"
            
        best_plan['strategy'] = strategy
        best_plan['predicted_productivity'] = best_prod
        
        self.db.insert_scenario(
            scenario_type="Golden_Plan_Optimal", quarter=quarter_input, department=department_input,
            target_prod=target_prod, pred_prod=best_prod, overtime=best_plan['over_time'],
            incentive=best_plan['incentive'], workers=best_plan['no_of_workers']
        )
        print(f" [DEBUG] Optimizer found plan. Sending to DB...")
        self.db.insert_scenario(
            "Golden_Plan_Optimal", quarter_input, department_input,
            target_prod, best_plan['predicted_productivity'], 
            best_plan['over_time'], best_plan['incentive'], best_plan['no_of_workers']
        )
        
        return best_plan