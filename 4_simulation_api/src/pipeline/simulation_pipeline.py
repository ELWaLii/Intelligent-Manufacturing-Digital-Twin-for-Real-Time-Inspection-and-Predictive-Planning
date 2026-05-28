import os
import joblib
import pandas as pd
from src.pipeline.db_helper import PostgreSQLHelper

class SimulationPipeline:
    def __init__(self):
        self.model = joblib.load(os.path.join('models', 'productivity_rf_model.pkl'))
        self.scaler = joblib.load(os.path.join('models', 'feature_scaler.pkl'))
        self.label_encoders = joblib.load(os.path.join('models', 'label_encoders.pkl'))
        self.feature_list = joblib.load(os.path.join('models', 'feature_list.pkl'))
        self.db = PostgreSQLHelper()

    def predict_custom_scenario(self, quarter_input, department_input, day_input, team_input, target_prod, overtime_input, incentive_input, workers_input):
        try:
            q_enc = self.label_encoders['quarter'].transform([quarter_input])[0]
            d_enc = self.label_encoders['department'].transform([department_input])[0]
            day_enc = self.label_encoders['day'].transform([day_input])[0]
            
            scenario_dict = {
                'quarter': q_enc, 'department': d_enc, 'day': day_enc, 'team': team_input,
                'targeted_productivity': target_prod, 'smv': 22.0, 'wip': 500.0, 'over_time': overtime_input,
                'incentive': incentive_input, 'no_of_workers': workers_input,
                'idle_time': 0.0, 'idle_men': 0.0, 'no_of_style_change': 0.0,
                'month': 2, 'day_of_month': 15, 'week_of_year': 7,
                'over_time_per_worker': overtime_input / (workers_input + 1e-5),
                'incentive_per_worker': incentive_input / (workers_input + 1e-5),
                'idle_impact': 0.0, 'idle_ratio': 0.0,
                'incentive_target_ratio': incentive_input / (target_prod + 1e-5),
                'stress_index': (22.0 * 1) / (workers_input + 1e-5)
            }
            
            df_pred = pd.DataFrame([scenario_dict])[self.feature_list]
            pred_scaled = self.scaler.transform(df_pred)
            predicted_prod = self.model.predict(pred_scaled)[0]
            
            # تسجيل في قاعدة البيانات
            success, err = self.db.insert_scenario(
                scenario_type="Custom_What_If", 
                quarter=quarter_input, 
                department=department_input,
                target_prod=target_prod, 
                pred_prod=predicted_prod, 
                overtime=overtime_input,
                incentive=incentive_input, 
                workers=workers_input
            )
            
            if success:
                return {"status": "success", "prediction": predicted_prod}
            else:
                return {"status": "error", "message": err}
                
        except Exception as e:
            return {"status": "error", "message": f"Pipeline Error: {str(e)}"}