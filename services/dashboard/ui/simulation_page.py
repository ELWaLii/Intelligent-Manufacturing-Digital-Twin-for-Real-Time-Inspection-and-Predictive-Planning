"""
KAVE Intelligent Manufacturing — Simulation & Optimization Page
================================================================
What-If Scenario Simulator and AI-Powered Seasonal Golden Plan Optimizer.
Uses XGBoost for productivity prediction and Grid Search for optimization.
Results are persisted to PostgreSQL for historical analysis.

Author: KAVE Engineering Team
Version: 2.0.0
"""

import streamlit as st
import pandas as pd
import os
import sys
import base64

from src.pipeline.simulation_pipeline import SimulationPipeline
from src.pipeline.optimization_pipeline import OptimizationPipeline
from src.pipeline.db_helper import PostgreSQLHelper
from ui.theme import get_plotly_theme, render_kpi_card

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")


# ═══════════════════════════════════════════════════════════════════════════════
# Cached Resource Initialization
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data
def get_base64_image(image_path: str) -> str:
    """Load an image file and return its Base64-encoded string."""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return ""


@st.cache_resource
def init_db() -> PostgreSQLHelper:
    """Initialize the PostgreSQL database connection and create tables."""
    try:
        db = PostgreSQLHelper()
        db.initialize_database()
        return db
    except Exception as e:
        st.error(f"⚠️ Database initialization failed: {e}")
        return None


@st.cache_resource
def init_simulation_pipeline() -> SimulationPipeline:
    """Load the XGBoost model and create the simulation pipeline."""
    try:
        return SimulationPipeline()
    except Exception as e:
        st.error(f"⚠️ Simulation pipeline failed to load: {e}")
        return None


@st.cache_resource
def init_optimization_pipeline() -> OptimizationPipeline:
    """Load the XGBoost model for optimization search."""
    try:
        return OptimizationPipeline()
    except Exception as e:
        st.error(f"⚠️ Optimization pipeline failed to load: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Banner Component
# ═══════════════════════════════════════════════════════════════════════════════

def _render_banner():
    """Render the animated KAVE logo surveillance banner."""
    img_b64 = get_base64_image(LOGO_PATH)
    if img_b64:
        st.markdown(
            f'<div class="camera-surveillance-box" '
            f'style="background-image:url(\'data:image/png;base64,{img_b64}\');">'
            f'<div class="rec-text">● REC</div></div>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# What-If Scenario Simulator Tab
# ═══════════════════════════════════════════════════════════════════════════════

def _render_what_if_tab(sim_pipeline: SimulationPipeline):
    """
    Render the What-If Scenario Simulator.
    Users configure factory parameters and the XGBoost model predicts
    the achievable actual productivity.
    """
    st.header("🔮 What-If Scenario Simulator")
    st.markdown(
        "Modify factory resources and instantly predict the **actual productivity** "
        "using the trained XGBoost engine. Results are automatically saved to PostgreSQL."
    )

    # ── Scenario Configuration ──
    with st.expander("⚙️ Scenario Configuration", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            quarter = st.selectbox(
                "Season / Quarter",
                ["Quarter1", "Quarter2", "Quarter3", "Quarter4", "Quarter5"],
                help="Select the production season. Different quarters have varying demand patterns.",
            )
            department = st.selectbox(
                "Department",
                ["sewing", "finishing"],
                help="Choose the garment production department to simulate.",
            )
            day = st.selectbox(
                "Day of Week",
                ["Thursday", "Saturday", "Sunday", "Monday", "Tuesday", "Wednesday"],
                help="Select the working day. Productivity can vary across the week.",
            )

        with col2:
            team = st.slider(
                "Team Number",
                min_value=1, max_value=12, value=1,
                help="Team ID (1-12). Each team may have different performance baselines.",
            )
            target_prod = st.slider(
                "Targeted Productivity",
                min_value=0.1, max_value=1.0, value=0.80, step=0.05,
                help="The productivity target set by management (0.0 to 1.0).",
            )
            workers = st.slider(
                "Total Workers Allocated",
                min_value=5, max_value=60, value=30,
                help="Number of workers assigned to the production line.",
            )

        with col3:
            overtime = st.number_input(
                "Total Overtime Minutes",
                min_value=0, max_value=10000, value=2000, step=500,
                help="Total overtime minutes allocated across the line.",
            )
            incentive = st.number_input(
                "Incentives Budget ($)",
                min_value=0, max_value=200, value=30, step=10,
                help="Financial incentive budget per team in USD.",
            )

    # ── Run Simulation ──
    if st.button("🚀 Run Simulator Engine", key="sim_btn", use_container_width=True):
        if sim_pipeline is None:
            st.error("❌ Simulation pipeline is not loaded. Check model files.")
            return

        with st.spinner("Processing scenario using XGBoost Engine..."):
            response = sim_pipeline.predict_custom_scenario(
                quarter_input=quarter,
                department_input=department,
                day_input=day,
                team_input=team,
                target_prod=target_prod,
                overtime_input=overtime,
                incentive_input=incentive,
                workers_input=workers,
            )

            if isinstance(response, dict) and response.get("status") == "success":
                predicted_res = response["prediction"]
                st.success("### ✅ Simulation Completed & Saved to PostgreSQL!")

                # ── Result Metrics ──
                m1, m2, m3 = st.columns(3)
                m1.metric(
                    label="🎯 Targeted Productivity",
                    value=f"{target_prod * 100:.1f}%",
                )
                if predicted_res >= target_prod:
                    m2.metric(
                        label="📈 Predicted Actual Productivity",
                        value=f"{predicted_res * 100:.2f}%",
                        delta=f"+{(predicted_res - target_prod) * 100:.1f}% Above Target",
                    )
                else:
                    m2.metric(
                        label="📉 Predicted Actual Productivity",
                        value=f"{predicted_res * 100:.2f}%",
                        delta=f"-{(target_prod - predicted_res) * 100:.1f}% Below Target",
                    )

                # ── Business Impact Estimate ──
                efficiency = predicted_res / (target_prod + 1e-9)
                m3.metric(
                    label="⚡ Efficiency Ratio",
                    value=f"{efficiency * 100:.1f}%",
                    help="Predicted / Target productivity ratio.",
                )

            else:
                error_msg = response.get("message") if isinstance(response, dict) else "Unknown Error"
                st.error(f"❌ Simulation failed: {error_msg}")


# ═══════════════════════════════════════════════════════════════════════════════
# Golden Plan Optimizer Tab
# ═══════════════════════════════════════════════════════════════════════════════

def _render_optimizer_tab(opt_pipeline: OptimizationPipeline):
    """
    Render the AI Seasonal Operations Optimizer.
    Scans hundreds of shift configurations using Grid Search to find
    the most cost-effective plan that meets the productivity target.
    """
    st.header("🎯 AI Seasonal Operations Optimizer")
    st.markdown(
        "Let the AI scan **hundreds of shift configurations** to generate the "
        "most cost-effective **Golden Plan** that meets your productivity target."
    )

    # ── Optimization Configuration ──
    with st.expander("⚙️ Optimization Parameters", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            opt_quarter = st.selectbox(
                "Target Quarter",
                ["Quarter1", "Quarter2", "Quarter3", "Quarter4", "Quarter5"],
                key="opt_q",
                help="The quarter/season to optimize for.",
            )
        with c2:
            opt_dept = st.selectbox(
                "Target Department",
                ["sewing", "finishing"],
                key="opt_d",
                help="The department to optimize.",
            )
        with c3:
            opt_target = st.slider(
                "Required Productivity Target",
                min_value=0.5, max_value=0.95, value=0.75, step=0.05,
                key="opt_t",
                help="Minimum productivity level the plan must achieve.",
            )

    # ── Run Optimizer ──
    if st.button("🌟 Generate Golden Plan", key="opt_btn", use_container_width=True):
        if opt_pipeline is None:
            st.error("❌ Optimization pipeline is not loaded. Check model files.")
            return

        with st.spinner("Scanning scenario combinations via Grid Search..."):
            response = opt_pipeline.find_best_seasonal_plan(
                quarter_input=opt_quarter,
                department_input=opt_dept,
                target_prod=opt_target,
            )

            if isinstance(response, dict) and response.get("status") == "success":
                best_plan = response["plan"]
                st.success("### 🌟 THE AI GOLDEN PLAN HAS BEEN FOUND!")

                # ── Plan Results ──
                r1, r2, r3, r4 = st.columns(4)
                r1.metric(
                    "📋 Strategy",
                    best_plan["strategy"][:30],
                    help=best_plan["strategy"],
                )
                r2.metric(
                    "👷 Workers",
                    f"{best_plan['no_of_workers']}",
                )
                r3.metric(
                    "⏱️ Overtime",
                    f"{best_plan['over_time']} min",
                )
                r4.metric(
                    "💰 Incentive",
                    f"${best_plan['incentive']}",
                )

                # ── Predicted productivity ──
                pred = best_plan["predicted_productivity"]
                st.info(
                    f"📈 **Expected Achievable Productivity under this plan:** "
                    f"**{pred * 100:.2f}%** (Your target was {opt_target * 100:.1f}%)"
                )

            else:
                error_msg = response.get("message") if isinstance(response, dict) else "Unknown Error"
                st.error(f"❌ Optimization failed: {error_msg}")


# ═══════════════════════════════════════════════════════════════════════════════
# Main Entry Point (exported for master app.py)
# ═══════════════════════════════════════════════════════════════════════════════

def run_simulation():
    """
    Main entry function for the Simulation & Optimization module.
    Called by the master app.py within the Simulation tab.
    """
    # ── Initialize resources ──
    db_manager = init_db()
    sim_pipeline = init_simulation_pipeline()
    opt_pipeline = init_optimization_pipeline()

    # ── Render banner ──
    _render_banner()
    st.markdown("---")

    # ── Sub-tabs for Simulation vs Optimization ──
    sub_tab1, sub_tab2 = st.tabs([
        "🔮 What-If Scenario Simulator",
        "🎯 Seasonal Golden Plan Optimizer",
    ])

    with sub_tab1:
        _render_what_if_tab(sim_pipeline)

    with sub_tab2:
        _render_optimizer_tab(opt_pipeline)
