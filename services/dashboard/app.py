"""
KAVE Intelligent Manufacturing — Master Dashboard
===================================================
Unified Streamlit entry point that orchestrates the Simulation &
Optimization module and the Real-Time Vision Inspection module
under a single, professionally themed application.

Services: Streamlit (port 8501)
Dependencies: PostgreSQL, Redis, Vision Engine (FastAPI)
Author: KAVE Engineering Team
Version: 2.0.0
"""

import streamlit as st
import os
import sys

# ── Ensure project root is on Python path ──────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# ── Logo path ──────────────────────────────────────────────────────────────────
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")

# ── Page Configuration (must be first Streamlit call) ──────────────────────────
try:
    from PIL import Image
    if os.path.exists(LOGO_PATH):
        _icon = Image.open(LOGO_PATH)
    else:
        _icon = "🏭"
except Exception:
    _icon = "🏭"

st.set_page_config(
    page_title="KAVE Intelligent Manufacturing",
    page_icon=_icon,
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "### KAVE Intelligent Manufacturing v2.0\n"
                 "Enterprise-Grade Digital Twin & Quality Control Platform.",
    },
)

# ── Inject Corporate Blue Theme ────────────────────────────────────────────────
from ui.theme import inject_corporate_theme, render_sidebar_branding

inject_corporate_theme()
render_sidebar_branding(logo_path=LOGO_PATH)

# ── Import Page Modules ────────────────────────────────────────────────────────
from ui.simulation_page import run_simulation
from ui.vision_page import run_vision
from src.components.chat_agent import render_chatbot

# ── Intro Landing Screen ───────────────────────────────────────────────────────
intro_b64 = ""
if os.path.exists(LOGO_PATH):
    try:
        import base64
        with open(LOGO_PATH, "rb") as img_file:
            intro_b64 = base64.b64encode(img_file.read()).decode()
    except Exception:
        pass

if intro_b64:
    st.markdown(
        f'<style>'
        f'@keyframes kaveFadeIn {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}'
        f'.kave-hero-wrapper {{'
        f'  display: flex; flex-direction: column; align-items: center; justify-content: center;'
        f'  padding: 3rem 2rem; margin: 1rem auto 2rem auto; max-width: 600px;'
        f'  background: rgba(255, 255, 255, 0.95);'
        f'  border-radius: 24px;'
        f'  box-shadow: 0 8px 40px rgba(0,180,216,0.25), 0 0 60px rgba(0,180,216,0.10);'
        f'  backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);'
        f'  border: 1px solid rgba(0,180,216,0.3);'
        f'  animation: kaveFadeIn 1.5s ease-in-out;'
        f'}}'
        f'.kave-hero-wrapper img {{'
        f'  width: 150px; border-radius: 16px; margin-bottom: 1rem;'
        f'  filter: drop-shadow(0 4px 12px rgba(0,0,0,0.15));'
        f'}}'
        f'.kave-hero-wrapper .hero-title {{'
        f'  font-family: "Inter", sans-serif; font-size: 3rem; font-weight: 900;'
        f'  letter-spacing: 4px; color: #0B101E !important; margin: 0;'
        f'}}'
        f'.kave-hero-wrapper .hero-subtitle {{'
        f'  font-size: 1.1rem; color: #475569 !important; font-weight: 400;'
        f'  letter-spacing: 1px; margin-top: 0.5rem;'
        f'}}'
        f'</style>'
        f'<div class="kave-hero-wrapper">'
        f'<img src="data:image/png;base64,{intro_b64}" alt="KAVE Logo" />'
        f'<div class="hero-title">KAVE</div>'
        f'<div class="hero-subtitle">Intelligent Manufacturing Digital Twin</div>'
        f'</div>',
        unsafe_allow_html=True
    )
else:
    st.markdown(
        '<div class="kave-intro-container">'
        '<div style="font-size: 5rem; text-shadow: 0 0 20px rgba(0,180,216,0.4);">🏭</div>'
        '<h1 class="kave-intro-title">KAVE</h1>'
        '<p class="kave-intro-subtitle">Intelligent Manufacturing Digital Twin</p>'
        '</div>',
        unsafe_allow_html=True
    )

st.markdown("---")

# ── Main Dashboard Content ─────────────────────────────────────────────────────
st.markdown('<div class="main-dashboard-content">', unsafe_allow_html=True)
# (Removed generic header since we now have the Intro Screen)

# ── Grafana Redirect Button ───────────────────────────────────────────────────
st.markdown(
    '<a href="http://localhost:3000/d/dwh-analytics" target="_blank" class="grafana-btn" '
    'style="color: #FFFFFF !important; font-weight: 800 !important; text-decoration: none !important;">'
    '📺 Open Live Grafana IoT Data Warehouse</a>',
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)

# ── Main Navigation Tabs ──────────────────────────────────────────────────────
main_tab1, main_tab2, main_tab3 = st.tabs([
    "📊 Resource Simulation & Planning",
    "👁️ Vision Quality Inspection",
    "🤖 Database AI Agent",
])

with main_tab1:
    run_simulation()

with main_tab2:
    run_vision()

with main_tab3:
    render_chatbot()

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="kave-footer">'
    'KAVE Intelligent Manufacturing Platform v3.0 &mdash; '
    'Powered by XGBoost, PaDiM &amp; PatchCore Dual-Pipeline (WideResNet-50-2), Gemini 1.5 Flash, Redis, InfluxDB &amp; PostgreSQL'
    '</div>',
    unsafe_allow_html=True,
)
st.markdown('</div>', unsafe_allow_html=True) # End of main-dashboard-content
