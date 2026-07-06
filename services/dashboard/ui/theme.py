"""
KAVE Intelligent Manufacturing — Light Blue & Green Theme System
=============================================================
Unified CSS theme injection for the entire Streamlit application.
Provides a premium, enterprise-grade visual identity using a
Dark Background with Light Blue & Green accents.

Author: KAVE Engineering Team
Version: 3.0.0
"""

import streamlit as st
import base64
import os

# ═══════════════════════════════════════════════════════════════════════════════
# Color Palette Constants — Light Blue & Green on Dark
# ═══════════════════════════════════════════════════════════════════════════════
NAVY_900 = "#0B101E"       # Deep Steel Grey/Black (Industry)
NAVY_800 = "#151B2B"       # Slightly lighter for panels
NAVY_700 = "#1F283E"       # Elevated surfaces
NAVY_600 = "#2A3651"       # Hover states / borders
AZURE_500 = "#00B4D8"      # Light Blue (Primary Accents)
AZURE_400 = "#48CAE4"      # Primary hover
SKY_300 = "#90E0EF"        # Accents / highlights
SKY_200 = "#ADE8F4"        # Secondary accents
ICE_100 = "#CAF0F8"        # Subtle highlights
WHITE = "#F8FAFC"          # Primary text
GRAY_400 = "#94A3B8"       # Secondary text
GRAY_600 = "#475569"       # Muted text / borders
SUCCESS = "#52B788"        # Light Green (Healthy/Positive)
WARNING = "#F59E0B"        # Amber for warnings
DANGER = "#EF4444"         # Red for anomalies/errors/critical

# Plotly chart color sequence matching the Light Blue & Green theme
PLOTLY_COLORS = [
    "#00B4D8", "#52B788", "#48CAE4", "#151B2B",
    "#CAF0F8", "#90E0EF", "#0B101E", "#F59E0B"
]


def _get_corporate_css() -> str:
    """
    Generate the complete CSS stylesheet.
    This is the single source of truth for all visual styling in the app.

    Returns:
        str: Complete HTML <style> block for Streamlit injection.
    """
    return f"""
    <style>
    /* ═══════════════════════════════════════════════════════════════════════
       KAVE Enterprise Design System v3.0
       ═══════════════════════════════════════════════════════════════════════ */

    /* ─── Typography: Google Fonts Inter ─── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }}

    /* ─── Fix Streamlit Dimming Issue ─── */
    [data-testid="stDataFrame"], [data-testid="stMetric"], .element-container {{
        opacity: 1 !important; 
        transition: none !important;
    }}

    /* ─── Global App Background ─── */
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(165deg, {NAVY_900} 0%, #0D1424 50%, {NAVY_800} 100%) !important;
        color: {WHITE} !important;
    }}

    [data-testid="stMain"] {{
        background: transparent !important;
    }}

    /* ─── Header Bar ─── */
    [data-testid="stHeader"] {{
        background: rgba(11, 15, 25, 0.85) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border-bottom: 1px solid rgba(0, 180, 216, 0.15) !important;
    }}

    /* ─── Sidebar ─── */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {NAVY_800} 0%, #0B101E 100%) !important;
        border-right: 1px solid rgba(0, 180, 216, 0.2) !important;
    }}

    [data-testid="stSidebar"] [data-testid="stMarkdown"] {{
        color: {WHITE} !important;
    }}

    /* ─── Animations ─── */
    @keyframes fadeInUp {{
        from {{ opacity: 0; transform: translateY(24px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    @keyframes fadeIn {{
        from {{ opacity: 0; }}
        to {{ opacity: 1; }}
    }}

    @keyframes pulseSuccess {{
        0%, 100% {{ box-shadow: 0 0 5px rgba(82, 183, 136, 0.4); }}
        50% {{ box-shadow: 0 0 15px rgba(82, 183, 136, 0.9), 0 0 25px rgba(82, 183, 136, 0.6); }}
    }}

    /* Applies globally for page load */
    .stApp {{
        animation: fadeIn 1s ease-out;
    }}

    /* ─── Intro Screen Classes ─── */
    .kave-intro-container {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 4rem 2rem;
        margin-bottom: 2rem;
        animation: fadeIn 1.2s ease-in-out;
    }}

    .kave-intro-logo {{
        width: 150px;
        margin-bottom: 1rem;
        border-radius: 16px;
        box-shadow: 0 0 30px rgba(0, 180, 216, 0.3);
    }}

    .kave-intro-title {{
        font-family: 'Inter', sans-serif;
        font-size: 3.5rem;
        font-weight: 900;
        letter-spacing: 4px;
        color: {AZURE_500};
        margin: 0;
        text-shadow: 0 0 20px rgba(0, 180, 216, 0.4);
    }}

    .kave-intro-subtitle {{
        font-size: 1.2rem;
        color: {GRAY_400};
        font-weight: 400;
        letter-spacing: 1px;
        margin-top: 0.5rem;
    }}

    .main-dashboard-content {{
        animation: fadeInUp 1s ease-out 0.5s both;
    }}

    /* ─── Typography ─── */
    h1 {{
        color: {WHITE} !important;
        font-weight: 800 !important;
        letter-spacing: -0.5px !important;
        font-size: 2rem !important;
    }}

    h2 {{
        color: {SKY_300} !important;
        font-weight: 700 !important;
        letter-spacing: -0.3px !important;
    }}

    h3 {{
        color: {AZURE_400} !important;
        font-weight: 600 !important;
    }}

    p, li, span, label, div {{
        color: {WHITE} !important;
    }}

    /* ─── Buttons: Light Blue Gradient with Glow ─── */
    div.stButton > button {{
        background: linear-gradient(135deg, {AZURE_500} 0%, {AZURE_400} 100%) !important;
        color: {NAVY_900} !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.6rem 1.8rem !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
        letter-spacing: 0.3px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 15px rgba(0, 180, 216, 0.3) !important;
        text-transform: none !important;
    }}

    div.stButton > button:hover {{
        transform: translateY(-3px) !important;
        box-shadow: 0 8px 30px rgba(0, 180, 216, 0.5) !important;
        background: linear-gradient(135deg, {AZURE_400} 0%, {SKY_300} 100%) !important;
    }}

    div.stButton > button:active {{
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0, 180, 216, 0.4) !important;
    }}

    /* ─── Metric Cards: Glassmorphism ─── */
    [data-testid="stMetric"] {{
        background: linear-gradient(135deg, rgba(21, 27, 43, 0.8) 0%, rgba(11, 15, 25, 0.9) 100%) !important;
        border: 1px solid rgba(0, 180, 216, 0.25) !important;
        border-radius: 14px !important;
        padding: 1.2rem 1rem !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(0, 180, 216, 0.1) !important;
        transition: all 0.3s ease !important;
        animation: fadeInUp 0.6s ease-out !important;
    }}

    [data-testid="stMetric"]:hover {{
        border-color: rgba(0, 180, 216, 0.5) !important;
        box-shadow: 0 8px 32px rgba(0, 180, 216, 0.2), inset 0 1px 0 rgba(0, 180, 216, 0.15) !important;
        transform: translateY(-2px) !important;
    }}

    [data-testid="stMetricLabel"] {{
        color: {GRAY_400} !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.8px !important;
    }}

    [data-testid="stMetricValue"] {{
        color: {WHITE} !important;
        font-size: 1.8rem !important;
        font-weight: 800 !important;
    }}

    [data-testid="stMetricDelta"] > div {{
        font-weight: 600 !important;
        font-size: 0.85rem !important;
    }}

    /* ─── Tabs: Light Blue Underline ─── */
    [data-baseweb="tab-list"] {{
        background-color: transparent !important;
        border-bottom: 2px solid rgba(0, 180, 216, 0.15) !important;
        gap: 0 !important;
    }}

    button[data-baseweb="tab"] {{
        color: {GRAY_400} !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        padding: 0.75rem 1.5rem !important;
        border: none !important;
        background: transparent !important;
        transition: all 0.3s ease !important;
        border-bottom: 3px solid transparent !important;
        margin-bottom: -2px !important;
    }}

    button[data-baseweb="tab"]:hover {{
        color: {SKY_300} !important;
        background: rgba(0, 180, 216, 0.08) !important;
    }}

    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {SKY_300} !important;
        font-weight: 700 !important;
        border-bottom: 3px solid {AZURE_500} !important;
        background: rgba(0, 180, 216, 0.05) !important;
    }}

    /* ─── Select Boxes ─── */
    div[data-baseweb="select"] > div {{
        background-color: {NAVY_700} !important;
        border: 1px solid rgba(0, 180, 216, 0.3) !important;
        border-radius: 10px !important;
        transition: all 0.25s ease !important;
    }}

    div[data-baseweb="select"] > div:hover {{
        border-color: {AZURE_500} !important;
    }}

    div[data-baseweb="select"] > div:focus-within {{
        border-color: {SKY_300} !important;
        box-shadow: 0 0 0 3px rgba(0, 180, 216, 0.15) !important;
    }}

    div[data-baseweb="select"] span,
    div[data-baseweb="select"] div {{
        color: {WHITE} !important;
    }}

    /* Dropdown Options */
    div[data-baseweb="popover"] div[role="listbox"] {{
        background-color: {NAVY_700} !important;
        border: 1px solid rgba(0, 180, 216, 0.3) !important;
        border-radius: 10px !important;
    }}

    li[role="option"] {{
        background-color: {NAVY_700} !important;
        color: {WHITE} !important;
        transition: all 0.15s ease !important;
    }}

    li[role="option"]:hover {{
        background-color: {AZURE_500} !important;
        color: {NAVY_900} !important;
    }}

    /* ─── Sliders ─── */
    div[data-baseweb="slider"] {{
        margin-top: 16px !important;
    }}

    div[data-baseweb="slider"] > div > div > div:first-child {{
        height: 6px !important;
        border-radius: 3px !important;
        background: linear-gradient(90deg, {AZURE_500}, {SKY_300}) !important;
    }}

    div[role="slider"] {{
        width: 22px !important;
        height: 22px !important;
        border: 3px solid {AZURE_500} !important;
        background-color: {WHITE} !important;
        box-shadow: 0 0 10px rgba(0, 180, 216, 0.4) !important;
        transition: all 0.2s ease !important;
        margin-top: -9px !important;
    }}

    div[role="slider"]:hover {{
        box-shadow: 0 0 20px rgba(0, 180, 216, 0.7) !important;
        transform: scale(1.15) !important;
        cursor: grab !important;
    }}

    div[role="slider"]:active {{
        cursor: grabbing !important;
    }}

    /* ─── Number Inputs ─── */
    input[type="number"] {{
        background-color: {NAVY_700} !important;
        border: 1px solid rgba(0, 180, 216, 0.3) !important;
        border-radius: 8px !important;
        color: {WHITE} !important;
        padding: 0.5rem !important;
        transition: all 0.25s ease !important;
    }}

    input[type="number"]:focus {{
        border-color: {SKY_300} !important;
        box-shadow: 0 0 0 3px rgba(0, 180, 216, 0.15) !important;
    }}

    /* ─── Text Inputs ─── */
    .stTextInput input, .stChatInput textarea {{
        background-color: {NAVY_700} !important;
        border: 1px solid rgba(0, 180, 216, 0.3) !important;
        border-radius: 8px !important;
        color: {WHITE} !important;
    }}

    /* ─── Expanders ─── */
    [data-testid="stExpander"] {{
        background: rgba(21, 27, 43, 0.5) !important;
        border: 1px solid rgba(0, 180, 216, 0.2) !important;
        border-radius: 12px !important;
        transition: all 0.3s ease !important;
    }}

    [data-testid="stExpander"]:hover {{
        border-color: rgba(0, 180, 216, 0.4) !important;
    }}

    [data-testid="stExpander"] summary {{
        color: {SKY_200} !important;
        font-weight: 600 !important;
    }}

    /* ─── File Uploader ─── */
    [data-testid="stFileUploader"] {{
        background: rgba(21, 27, 43, 0.4) !important;
        border: 2px dashed rgba(0, 180, 216, 0.3) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        transition: all 0.3s ease !important;
    }}

    [data-testid="stFileUploader"]:hover {{
        border-color: {AZURE_500} !important;
        background: rgba(21, 27, 43, 0.6) !important;
    }}

    /* ─── Toggle Switch ─── */
    [data-testid="stToggle"] label span {{
        color: {WHITE} !important;
    }}

    /* ─── Info / Success / Warning / Error Boxes ─── */
    [data-testid="stAlert"] {{
        border-radius: 10px !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
    }}

    /* ─── Dataframe / Table ─── */
    [data-testid="stDataFrame"] {{
        border-radius: 12px !important;
        overflow: hidden !important;
    }}

    /* ─── Divider / Horizontal Rule ─── */
    hr {{
        border-color: rgba(0, 180, 216, 0.15) !important;
        margin: 1.5rem 0 !important;
    }}

    /* ─── Scrollbar Styling ─── */
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}

    ::-webkit-scrollbar-track {{
        background: {NAVY_900};
    }}

    ::-webkit-scrollbar-thumb {{
        background: {NAVY_600};
        border-radius: 4px;
    }}

    ::-webkit-scrollbar-thumb:hover {{
        background: {AZURE_500};
    }}

    /* ─── Custom Component: KPI Card ─── */
    .kave-kpi-card {{
        background: linear-gradient(135deg, rgba(21, 27, 43, 0.9) 0%, rgba(11, 15, 25, 0.7) 100%);
        border: 1px solid rgba(0, 180, 216, 0.3);
        border-radius: 16px;
        padding: 1.5rem;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
    }}

    .kave-kpi-card:hover {{
        transform: translateY(-4px);
        box-shadow: 0 0 20px rgba(0, 180, 216, 0.6), inset 0 0 10px rgba(0, 180, 216, 0.2);
        border-color: rgba(0, 180, 216, 0.8);
    }}

    .kave-kpi-label {{
        color: {GRAY_400};
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        margin-bottom: 0.5rem;
    }}

    .kave-kpi-value {{
        color: {WHITE};
        font-size: 2.2rem;
        font-weight: 800;
        line-height: 1.1;
    }}

    .kave-kpi-delta {{
        font-size: 0.85rem;
        font-weight: 600;
        margin-top: 0.5rem;
    }}

    .kave-kpi-delta.positive {{ color: {SUCCESS}; }}
    .kave-kpi-delta.negative {{ color: {DANGER}; }}
    .kave-kpi-delta.neutral {{ color: {WARNING}; }}

    /* ─── Custom Component: Section Header ─── */
    .kave-section-header {{
        display: flex;
        align-items: center;
        gap: 12px;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid rgba(0, 180, 216, 0.2);
    }}

    .kave-section-header h3 {{
        margin: 0 !important;
        padding: 0 !important;
        color: {SKY_300} !important;
    }}

    /* ─── Custom Component: Status Badge ─── */
    .kave-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.3px;
    }}

    .kave-badge.online {{
        background: rgba(82, 183, 136, 0.15);
        color: {SUCCESS};
        border: 1px solid rgba(82, 183, 136, 0.3);
        animation: pulseSuccess 2s infinite;
    }}

    .kave-badge.offline {{
        background: rgba(239, 68, 68, 0.15);
        color: {DANGER};
        border: 1px solid rgba(239, 68, 68, 0.3);
    }}

    .kave-badge.warning {{
        background: rgba(245, 158, 11, 0.15);
        color: {WARNING};
        border: 1px solid rgba(245, 158, 11, 0.3);
    }}

    /* ─── Custom: Camera Surveillance Box ─── */
    @keyframes camera-pan {{
        0% {{ transform: scale(1); }}
        50% {{ transform: scale(1.015); }}
        100% {{ transform: scale(1); }}
    }}

    @keyframes blink {{
        0% {{ opacity: 1; }}
        50% {{ opacity: 0.2; }}
        100% {{ opacity: 1; }}
    }}

    .camera-surveillance-box {{
        width: 100%;
        height: 220px;
        background-size: contain;
        background-position: center center;
        background-repeat: no-repeat;
        background-color: {NAVY_800};
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(0, 180, 216, 0.2);
        animation: camera-pan 12s ease-in-out infinite;
        margin-bottom: 20px;
        position: relative;
        overflow: hidden;
    }}

    .camera-surveillance-box::before {{
        content: '';
        position: absolute;
        inset: 0;
        border-radius: 16px;
        border: 1px solid rgba(0, 180, 216, 0.3);
        pointer-events: none;
    }}

    .rec-text {{
        position: absolute;
        top: 14px;
        left: 14px;
        color: {DANGER};
        font-weight: 800;
        background-color: rgba(0, 0, 0, 0.85);
        padding: 5px 14px;
        border-radius: 8px;
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        letter-spacing: 2px;
        font-size: 13px;
        animation: blink 1.5s infinite;
        box-shadow: 0 0 12px rgba(239, 68, 68, 0.3);
    }}

    /* ─── Custom: Live Feed Placeholder ─── */
    .kave-feed-placeholder {{
        background: linear-gradient(135deg, rgba(21, 27, 43, 0.6) 0%, rgba(11, 15, 25, 0.8) 100%);
        border: 2px dashed rgba(0, 180, 216, 0.3);
        border-radius: 16px;
        padding: 3rem 2rem;
        text-align: center;
        color: {GRAY_400};
    }}

    .kave-feed-placeholder .icon {{
        font-size: 3rem;
        margin-bottom: 1rem;
        opacity: 0.6;
    }}

    /* ─── Custom: Footer ─── */
    .kave-footer {{
        text-align: center;
        padding: 2rem 0 1rem 0;
        color: {GRAY_600};
        font-size: 0.78rem;
        border-top: 1px solid rgba(0, 180, 216, 0.1);
        margin-top: 3rem;
    }}

    /* ─── Plotly Chart Overrides ─── */
    .js-plotly-plot .plotly .modebar {{
        right: 10px !important;
    }}

    /* ─── Glowing Grafana Button ─── */
    .grafana-btn {{
        display: block;
        width: 100%;
        text-align: center;
        font-size: 14px;
        font-weight: 800;
        color: #FFFFFF !important;
        background: linear-gradient(135deg, rgba(0, 180, 216, 0.8), rgba(72, 202, 228, 0.9));
        border: 2px solid {AZURE_500};
        border-radius: 10px;
        padding: 12px 16px;
        cursor: pointer;
        text-decoration: none !important;
        transition: all 0.3s ease;
        box-shadow: 0 0 10px rgba(0, 180, 216, 0.4), inset 0 0 5px rgba(0, 180, 216, 0.2);
        animation: pulseSuccess 2s infinite alternate;
    }}
    .grafana-btn:hover {{
        color: #FFFFFF !important;
        background: linear-gradient(135deg, {AZURE_400}, {AZURE_500});
        box-shadow: 0 0 20px rgba(0, 180, 216, 0.8), inset 0 0 10px rgba(0, 180, 216, 0.4);
        transform: translateY(-2px);
        text-decoration: none !important;
    }}
    .grafana-btn:visited, .grafana-btn:active, .grafana-btn:focus {{
        color: #FFFFFF !important;
        text-decoration: none !important;
    }}
    </style>
    """


def inject_corporate_theme():
    """
    Inject the complete CSS theme into the Streamlit app.
    Must be called once at the top of the main app.py after st.set_page_config().
    """
    st.markdown(_get_corporate_css(), unsafe_allow_html=True)


def render_sidebar_branding(logo_path: str = None):
    """
    Render the KAVE branding section in the sidebar with logo, 
    navigation links, and system status indicators.

    Args:
        logo_path: Absolute path to the logo image file.
    """
    with st.sidebar:
        # ── Logo ──
        if logo_path and os.path.exists(logo_path):
            try:
                with open(logo_path, "rb") as img_file:
                    logo_b64 = base64.b64encode(img_file.read()).decode()
                st.markdown(
                    f'<div style="text-align:center; margin-bottom:0.5rem;">'
                    f'<img src="data:image/png;base64,{logo_b64}" '
                    f'style="width:130px; border-radius:12px; '
                    f'border:2px solid rgba(0,180,216,0.4); '
                    f'background-color:#0B101E; padding:4px;" />'
                    f'</div>',
                    unsafe_allow_html=True
                )
            except Exception:
                st.markdown(
                    '<div style="text-align:center; font-size:3rem; margin-bottom:1rem;">🏭</div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                '<div style="text-align:center; font-size:3rem; margin-bottom:1rem;">🏭</div>',
                unsafe_allow_html=True
            )

        # ── Title ──
        st.markdown(
            '<h2 style="text-align:center; color:#00B4D8 !important; '
            'font-size:1.1rem; margin-top:0;">KAVE Command Center</h2>',
            unsafe_allow_html=True
        )

        st.markdown("---")

        # ── System Info ──
        st.info(
            "💡 **Navigation Guide**\n\n"
            "• **Simulation** — What-If scenarios & Golden Plans\n\n"
            "• **Vision** — Live feed, upload, & analytics\n\n"
            "• **Data Agent** — Ask business & live sensor queries"
        )

        st.markdown("---")

        # ── System Status ──
        st.markdown(
            '<div style="text-align:center;">'
            '<span class="kave-badge online">● System Online</span>'
            '</div>',
            unsafe_allow_html=True
        )


def render_kpi_card(label: str, value: str, delta: str = None, delta_type: str = "neutral") -> str:
    """
    Generate HTML for a custom KPI card with glassmorphism effect.

    Args:
        label: KPI metric label (e.g., "Scrap Rate").
        value: The displayed value (e.g., "2.4%").
        delta: Optional delta text (e.g., "+0.3% vs last week").
        delta_type: One of "positive", "negative", "neutral".

    Returns:
        str: HTML string for the KPI card.
    """
    delta_html = ""
    if delta:
        delta_html = f'<div class="kave-kpi-delta {delta_type}">{delta}</div>'

    return f"""
    <div class="kave-kpi-card">
        <div class="kave-kpi-label">{label}</div>
        <div class="kave-kpi-value">{value}</div>
        {delta_html}
    </div>
    """


def get_plotly_theme() -> dict:
    """
    Get a Plotly layout template matching the Light Blue/Green theme.
    Use with fig.update_layout(**get_plotly_theme()).

    Returns:
        dict: Plotly layout configuration dictionary.
    """
    return {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(21, 27, 43, 0.4)",
        "font": {"color": WHITE, "family": "Inter, sans-serif"},
        "title": {"font": {"color": SKY_300, "size": 16, "family": "Inter, sans-serif"}},
        "xaxis": {
            "gridcolor": "rgba(0, 180, 216, 0.1)",
            "zerolinecolor": "rgba(0, 180, 216, 0.2)",
            "tickfont": {"color": GRAY_400},
        },
        "yaxis": {
            "gridcolor": "rgba(0, 180, 216, 0.1)",
            "zerolinecolor": "rgba(0, 180, 216, 0.2)",
            "tickfont": {"color": GRAY_400},
        },
        "legend": {"font": {"color": GRAY_400}},
        "colorway": PLOTLY_COLORS,
        "margin": {"l": 40, "r": 20, "t": 50, "b": 40},
    }
