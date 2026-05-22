import os
import joblib
import pandas as pd
from src.pipeline.db_helper import PostgreSQLHelper

class SimulationPipeline:
    """
    كلاس مسؤول عن تنفيذ محاكاة الإنتاج والتنبؤ بالإنتاجية
    وتسجيل النتائج في قاعدة البيانات
    """
    def __init__(self):
        # تحميل الموديل والملحقات (Scalers, Encoders, Feature list)
        self.model = joblib.load(os.path.join('models', 'productivity_rf_model.pkl'))
        self.scaler = joblib.load(os.path.join('models', 'feature_scaler.pkl'))
        self.label_encoders = joblib.load(os.path.join('models', 'label_encoders.pkl'))
        self.feature_list = joblib.load(os.path.join('models', 'feature_list.pkl'))
        self.db = PostgreSQLHelper()

    def predict_custom_scenario(self, quarter_input, department_input, day_input, team_input, target_prod, overtime_input, incentive_input, workers_input):
        """
        تنفيذ المحاكاة: تحويل المدخلات -> تجهيز البيانات -> التنبؤ -> تسجيل النتيجة
        """
        # 1. تحويل البيانات الفئوية (Encoding)
        q_encoded = self.label_encoders['quarter'].transform([quarter_input])[0]
        d_encoded = self.label_encoders['department'].transform([department_input])[0]
        day_encoded = self.label_encoders['day'].transform([day_input])[0]
        
        # 2. حساب المتغيرات الهندسية (Feature Engineering)
        # لازم القيم دي تطابق تماماً الأعمدة اللي اتدرب عليها الموديل
        scenario_dict = {
            'quarter': q_encoded, 
            'department': d_encoded, 
            'day': day_encoded, 
            'team': team_input,
            'targeted_productivity': target_prod, 
            'smv': 22.0, 
            'wip': 500.0, 
            'over_time': overtime_input,
            'incentive': incentive_input, 
            'no_of_workers': workers_input,
            'idle_time': 0.0, 
            'idle_men': 0.0, 
            'no_of_style_change': 0.0,
            'month': 2, 
            'day_of_month': 15, 
            'week_of_year': 7,
            'over_time_per_worker': overtime_input / (workers_input + 1e-5),
            'incentive_per_worker': incentive_input / (workers_input + 1e-5),
            'idle_impact': 0.0, 
            'idle_ratio': 0.0,
            'incentive_target_ratio': incentive_input / (target_prod + 1e-5),
            'stress_index': (22.0 * (0.0 + 1)) / (workers_input + 1e-5)
        }
        
        # 3. تجهيز الـ DataFrame وضبط ترتيب الأعمدة حسب الـ feature_list
        scenario_df = pd.DataFrame([scenario_dict])[self.feature_list]
        
        # 4. الـ Scaling والتنبؤ
        scenario_scaled = self.scaler.transform(scenario_df)
        predicted_prod = self.model.predict(scenario_scaled)[0]
        
        print(f" [DEBUG] Prediction Finished: {predicted_prod}. Sending to DB...")
        
        # 5. تسجيل النتائج في قاعدة البيانات
        self.db.insert_scenario(
            scenario_type="Custom_What_If", 
            quarter=quarter_input, 
            department=department_input,
            target_prod=target_prod, 
            pred_prod=predicted_prod, 
            overtime=overtime_input,
            incentive=incentive_input, 
            workers=workers_input
        )
        
        return predicted_prod