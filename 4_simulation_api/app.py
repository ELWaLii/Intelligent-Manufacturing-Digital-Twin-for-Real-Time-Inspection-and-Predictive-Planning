import streamlit as st
import pandas as pd
import os
import sys
import base64
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.pipeline.simulation_pipeline import SimulationPipeline
from src.pipeline.optimization_pipeline import OptimizationPipeline
from src.pipeline.db_helper import PostgreSQLHelper

CAMERA_IMG_PATH = os.path.join(BASE_DIR, 'logo.png')

try:
    logo_image = Image.open(CAMERA_IMG_PATH)
except FileNotFoundError:
    logo_image = "🏭"

st.set_page_config(
    page_title="KAVE Intelligent Manufacturing", 
    layout="wide", 
    page_icon=logo_image
)

@st.cache_data
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return ""

@st.cache_resource
def init_db():
    db = PostgreSQLHelper()
    db.initialize_database()
    return db

db_manager = init_db()

sim_pipeline = SimulationPipeline()
opt_pipeline = OptimizationPipeline()

img_base64_str = get_base64_image(CAMERA_IMG_PATH)

modern_animations = f"""
<style>
[data-testid="stAppViewContainer"] {{
    background-color: #0B101E !important; 
    color: #FFFFFF !important;
}}
[data-testid="stSidebar"] {{
    background-color: #151E32 !important; 
}}
[data-testid="stHeader"] {{
    background-color: rgba(11, 16, 30, 0.8) !important; 
}}
h1, h2, h3, h4, h5, h6, p, label {{
    color: #E6edf3 !important;
}}
@keyframes fadeInUp {{
    from {{ opacity: 0; transform: translateY(30px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}
.stApp {{
    animation: fadeInUp 1.2s ease-out;
}}
div.stButton > button {{
    transition: all 0.3s ease-in-out !important;
    border-radius: 8px !important;
    border: 1px solid #007BFF !important;
    background-color: transparent !important;
    color: #007BFF !important;
}}
div.stButton > button:hover {{
    transform: translateY(-3px) !important;
    box-shadow: 0 6px 20px rgba(0, 123, 255, 0.4) !important;
    background-color: #007BFF !important;
    color: #ffffff !important;
}}
@keyframes camera-pan {{
    0% {{ transform: scale(1); }}
    50% {{ transform: scale(1.02); }}
    100% {{ transform: scale(1); }}
}}
@keyframes blink {{
    0% {{ opacity: 1; }}
    50% {{ opacity: 0.2; }}
    100% {{ opacity: 1; }}
}}
.camera-surveillance-box {{
    width: 100%;
    height: 250px; 
    background-image: url('data:image/png;base64,{img_base64_str}');
    background-size: contain; 
    background-position: center center;
    background-repeat: no-repeat;
    background-color: #ffffff; 
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0, 123, 255, 0.15);
    border: 1px solid rgba(0, 123, 255, 0.3);
    animation: camera-pan 10s ease-in-out infinite; 
    margin-bottom: 25px;
    position: relative;
}}
.rec-text {{
    position: absolute;
    top: 15px;
    left: 15px;
    color: #FF3B30;
    font-weight: 800;
    background-color: rgba(0,0,0,0.85);
    padding: 5px 12px;
    border-radius: 6px;
    font-family: 'Courier New', monospace;
    letter-spacing: 2px;
    font-size: 14px;
    animation: blink 1.5s infinite;
    box-shadow: 0 0 10px rgba(255, 59, 48, 0.4);
}}
div[data-baseweb="slider"] {{
    margin-top: 20px !important;
}}
div[data-baseweb="slider"] > div > div > div:first-child {{
    height: 8px !important;
    border-radius: 4px !important;
}}
div[role="slider"] {{
    width: 24px !important;
    height: 24px !important;
    border: 4px solid #007BFF !important;
    background-color: #ffffff !important;
    box-shadow: 0 0 10px rgba(0, 123, 255, 0.5) !important;
    transition: box-shadow 0.2s ease !important; 
    margin-top: -10px !important; 
}}
div[role="slider"]:hover {{
    box-shadow: 0 0 20px rgba(0, 123, 255, 1) !important;
    cursor: grab !important;
}}
div[role="slider"]:active {{
    cursor: grabbing !important;
}}
div[data-baseweb="select"] > div {{
    background-color: #151E32 !important;
    border: 1px solid rgba(0, 123, 255, 0.5) !important;
}}
div[data-baseweb="select"] span, 
div[data-baseweb="select"] div {{
    color: #FFFFFF !important;
}}
div[data-baseweb="popover"] div[role="listbox"] {{
    background-color: #151E32 !important; 
}}
li[role="option"] {{
    background-color: #151E32 !important; 
    color: #FFFFFF !important; 
}}
li[role="option"]:hover {{
    background-color: #007BFF !important; 
    color: #FFFFFF !important;
}}
</style>
<div class="camera-surveillance-box">
    <div class="rec-text">● REC</div>
</div>
"""
st.markdown(modern_animations, unsafe_allow_html=True)

st.markdown("---")

if img_base64_str:
    st.sidebar.markdown(f'<div style="text-align: center;"><img src="data:image/png;base64,{img_base64_str}" style="width: 150px; border-radius: 10px; border: 2px solid #007BFF; background-color: #ffffff;"></div>', unsafe_allow_html=True)

st.sidebar.markdown("<h2 style='text-align: center; color: #007BFF;'>KAVE Navigation Hub</h2>", unsafe_allow_html=True)
st.sidebar.markdown("---")

grafana_url = "http://localhost:3000/goto/afmudlldpckjkf?orgId=1" 
st.sidebar.markdown(f'<a href="{grafana_url}" target="_blank"><button style="width:100%;font-family:sans-serif;font-size:15px;font-weight:bold;color:white;background-color:#E65100;border:none;border-radius:5px;padding:12px;cursor:pointer;">📺 Go to Grafana Live CNC Monitoring</button></a>', unsafe_allow_html=True)
st.sidebar.markdown("---")
st.sidebar.info("💡 Hub Info: Use Grafana to monitor physical machines and Streamlit to simulate human resource plans.")

tab1, tab2 = st.tabs(["🔮 What-If Scenario Simulator", "🎯 Seasonal Golden Plan Optimizer"])

with tab1:
    st.header("Run Custom What-If Simulations")
    st.write("Modify factory resources and see the predicted actual productivity immediately.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        quarter = st.selectbox("Select Season / Quarter", ["Quarter1", "Quarter2", "Quarter3", "Quarter4", "Quarter5"])
        department = st.selectbox("Select Department", ["sewing", "finishing"])
        day = st.selectbox("Select Day of Week", ["Thursday", "Saturday", "Sunday", "Monday", "Tuesday", "Wednesday"])
    with col2:
        team = st.slider("Team Number", min_value=1, max_value=12, value=1)
        target_prod = st.slider("Targeted Productivity Target", min_value=0.1, max_value=1.0, value=0.80, step=0.05)
        workers = st.slider("Total Workers Allocated", min_value=5, max_value=60, value=30)
    with col3:
        overtime = st.number_input("Total Overtime Minutes (per line)", min_value=0, max_value=10000, value=2000, step=500)
        incentive = st.number_input("Total Incentives Budget ($)", min_value=0, max_value=200, value=30, step=10)

    if st.button("🚀 Run Simulator Engine", key="sim_btn"):
        with st.spinner("Processing scenario using XGBoost Engine..."):
            response = sim_pipeline.predict_custom_scenario(
                quarter_input=quarter, department_input=department, day_input=day,
                team_input=team, target_prod=target_prod, overtime_input=overtime,
                incentive_input=incentive, workers_input=workers
            )
            
            if isinstance(response, dict) and response.get("status") == "success":
                predicted_res = response["prediction"]
                st.success("### 💾 Simulation Completed & Saved to PostgreSQL!")
                m1, m2 = st.columns(2)
                m1.metric(label="Targeted Productivity Set", value=f"{target_prod*100:.1f}%")
                if predicted_res >= target_prod:
                    m2.metric(label="🔵 Predicted Actual Productivity", value=f"{predicted_res*100:.2f}%", delta=f"+{(predicted_res-target_prod)*100:.1f}% Above Target")
                else:
                    m2.metric(label="🔴 Predicted Actual Productivity", value=f"{predicted_res*100:.2f}%", delta=f"-{(target_prod-predicted_res)*100:.1f}% Below Target")
            else:
                error_msg = response.get("message") if isinstance(response, dict) else "Unknown Error"
                st.error(f"❌ Failed to save to database: {error_msg}")

with tab2:
    st.header("🎯 AI Seasonal Operations Optimizer")
    st.write("Let the system scan hundreds of shift configurations to generate the most cost-effective Golden Plan.")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        opt_quarter = st.selectbox("Select Target Quarter", ["Quarter1", "Quarter2", "Quarter3", "Quarter4", "Quarter5"], key="opt_q")
    with c2:
        opt_dept = st.selectbox("Select Target Department", ["sewing", "finishing"], key="opt_d")
    with c3:
        opt_target = st.slider("Required Productivity Target", min_value=0.5, max_value=0.95, value=0.75, step=0.05, key="opt_t")
        
    if st.button("🌟 Generate Golden Plan", key="opt_btn"):
        with st.spinner("Scanning scenario combinations via Grid Search..."):
            response = opt_pipeline.find_best_seasonal_plan(
                quarter_input=opt_quarter, department_input=opt_dept, target_prod=opt_target
            )
            
            if isinstance(response, dict) and response.get("status") == "success":
                best_plan = response["plan"]
                st.success("### 🌟 THE AI GOLDEN PLAN FOUND & SAVED TO POSTGRESQL!")
                r1, r2, r3, r4 = st.columns(4)
                r1.metric("Recommended Shift Strategy", best_plan['strategy'])
                r2.metric("Total Workers to Allocate", f"{best_plan['no_of_workers']} Workers")
                r3.metric("Allocated Overtime", f"{best_plan['over_time']} Mins")
                r4.metric("Incentives per Team", f"${best_plan['incentive']}")
                
                st.info(f"📈 **Expected Achievable Productivity under this plan:** {best_plan['predicted_productivity']*100:.2f}% (Your target was {opt_target*100:.1f}%)")
            else:
                error_msg = response.get("message") if isinstance(response, dict) else "Unknown Error"
                st.error(f"❌ Optimization failed or could not save to database: {error_msg}")