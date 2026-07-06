"""
KAVE Intelligent Manufacturing — Vision Quality Inspection Page
================================================================
Unified module combining three sub-tabs:
  1. Live Feed — Real-time camera inspection via Redis Streams
  2. Upload Inspection — On-demand single image analysis via FastAPI
  3. Analytics & KPIs — Business intelligence from PostgreSQL defect logs

Author: KAVE Engineering Team
Version: 2.0.0
"""

import os
import time
import io
import base64
import datetime

import streamlit as st
import pandas as pd
import plotly.express as px
import psycopg2
from PIL import Image
from redis import Redis

from ui.theme import get_plotly_theme, render_kpi_card

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration & Environment
# ═══════════════════════════════════════════════════════════════════════════════
REDIS_HOST = os.environ.get("REDIS_HOST", "kave_redis")
DB_HOST = os.environ.get("DB_HOST", "kave_db")
DB_PORT = int(os.environ.get("DB_PORT", 5432))
DB_NAME = os.environ.get("POSTGRES_DB", "kave_db")
DB_USER = os.environ.get("POSTGRES_USER", "admin")
DB_PASS = os.environ.get("POSTGRES_PASSWORD", "kave_pass")
VISION_API_URL = os.environ.get("VISION_API_URL", "http://kave_vision_engine:8000")

OUT_STREAM = "results_stream"


# ═══════════════════════════════════════════════════════════════════════════════
# Cached Connections
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_redis_client():
    """Create a cached Redis client for real-time stream reading."""
    try:
        client = Redis(host=REDIS_HOST, port=6379, db=0, socket_timeout=5)
        client.ping()
        return client
    except Exception as e:
        st.warning(f"⚠️ Redis connection unavailable: {e}")
        return None


@st.cache_data(ttl=10)
def load_defect_logs() -> pd.DataFrame:
    """
    Load defect logs from PostgreSQL with a 10-second cache TTL.
    Returns an empty DataFrame if the connection fails or no data exists.
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, database=DB_NAME,
            user=DB_USER, password=DB_PASS
        )
        query = (
            "SELECT id, timestamp, filename, anomaly_score, image_path "
            "FROM defect_logs ORDER BY timestamp DESC"
        )
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        # Graceful degradation: return empty DF instead of crashing
        return pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 1: Live Feed
# ═══════════════════════════════════════════════════════════════════════════════

def _render_live_feed():
    """
    Render the real-time metal nut inspection feed.
    Reads inference results from the Redis 'results_stream' published
    by the Vision Engine consumer worker.
    """
    st.markdown("### 🔴 Live Metal Nut Inspection (Edge Camera)")
    st.markdown(
        "Connect to the Redis live stream to see real-time AI inference "
        "results from the edge camera feed using our PaDiM real-time streaming pipeline."
    )

    is_live = st.toggle(
        "🎥 Start Live Camera Feed",
        value=False,
        help="Toggle to connect/disconnect from the Redis live inspection stream.",
    )

    col1, col2, col3 = st.columns([1.5, 1.5, 1])
    img_placeholder = col1.empty()
    heatmap_placeholder = col2.empty()
    status_placeholder = col3.empty()

    if not is_live:
        # ── Professional placeholder when feed is off ──
        st.markdown(
            '<div class="kave-feed-placeholder">'
            '<div class="icon">📹</div>'
            '<p style="font-size:1.1rem; font-weight:600; color:#94A3B8 !important;">'
            'Camera Feed Inactive</p>'
            '<p style="color:#475569 !important; font-size:0.9rem;">'
            'Toggle the button above to connect to the Redis live stream.<br>'
            'Ensure the Vision Producer and Vision Engine containers are running.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Connect to Redis ──
    redis_client = get_redis_client()
    if redis_client is None:
        st.error(
            "❌ **Cannot connect to Redis.**\n\n"
            "Please verify that the `kave_redis` container is running and "
            "the `REDIS_HOST` environment variable is correctly set."
        )
        return

    last_id = "$"

    while is_live:
        try:
            messages = redis_client.xread(
                {OUT_STREAM: last_id}, count=1, block=2000
            )

            if not messages:
                time.sleep(0.1)
                continue

            for stream, message_list in messages:
                for message_id, message_data in message_list:
                    last_id = message_id

                    # Decode message fields
                    filename = message_data[b"filename"].decode("utf-8")
                    score = float(message_data[b"score"].decode("utf-8"))
                    inf_ms = float(message_data[b"inference_ms"].decode("utf-8"))
                    is_anom = int(message_data[b"is_anomaly"].decode("utf-8")) == 1

                    # Decode images
                    orig_bytes = base64.b64decode(
                        message_data[b"original_b64"].decode("utf-8")
                    )
                    hm_bytes = base64.b64decode(
                        message_data[b"heatmap_b64"].decode("utf-8")
                    )

                    img_orig = Image.open(io.BytesIO(orig_bytes)).convert("RGB")
                    img_hm = Image.open(io.BytesIO(hm_bytes)).convert("RGB")

                    # Create overlay
                    img_orig_resized = img_orig.resize((224, 224))
                    overlay = Image.blend(img_orig_resized, img_hm, alpha=0.5)

                    # Update placeholders
                    img_placeholder.image(
                        img_orig, caption=f"Feed: {filename}",
                        use_container_width=True,
                    )
                    heatmap_placeholder.image(
                        overlay, caption="Defect Heatmap Overlay",
                        use_container_width=True,
                    )

                    with status_placeholder.container():
                        if is_anom:
                            st.error(
                                f"🚨 **REJECTED: ANOMALY**\n\nScore: `{score:.4f}`"
                            )
                        else:
                            st.success(
                                f"✅ **ACCEPTED: NORMAL**\n\nScore: `{score:.4f}`"
                            )
                        st.metric("⏱️ Latency", f"{inf_ms:.1f} ms")

        except Exception as e:
            st.warning(f"Waiting for incoming stream... ({e})")
            time.sleep(1)


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 2: Upload Inspection
# ═══════════════════════════════════════════════════════════════════════════════

def _render_upload_inspection():
    """
    Render the manual image upload tab for on-demand anomaly detection.
    Sends images to the Vision Engine FastAPI /predict endpoint.
    """
    st.markdown("### 📤 Manual Image Inspection")
    st.markdown(
        "Upload a metal nut image to run **PatchCore (WideResNet-50-2)** anomaly detection on demand for manual deep inspection. "
        "The image is sent to the Vision Engine API for inference."
    )

    # ── API Status Check ──
    with st.sidebar:
        st.markdown("---")
        st.markdown("##### 👁️ Vision Engine Status")
        try:
            import requests
            cfg = requests.get(f"{VISION_API_URL}/config", timeout=3).json()
            real_threshold = float(cfg.get("threshold", 0.5))
            st.markdown(
                '<span class="kave-badge online">● Engine Connected</span>',
                unsafe_allow_html=True,
            )
            st.caption(
                f"**Model:** {cfg.get('model', 'PatchCore')}\n\n"
                f"**Backbone:** WideResNet-50-2\n\n"
                f"**Threshold:** {real_threshold:.4f}"
            )
        except Exception:
            real_threshold = 0.5
            st.markdown(
                '<span class="kave-badge offline">● Engine Offline</span>',
                unsafe_allow_html=True,
            )
            st.caption("Start the Vision Engine container to enable uploads.")

    threshold = st.slider(
        "Override Detection Threshold",
        min_value=0.0, max_value=5.0, value=real_threshold, step=0.01,
        help="Adjust the anomaly score threshold. Lower = more sensitive.",
        key="vision_threshold_slider",
    )

    # ── File Upload ──
    uploaded = st.file_uploader(
        "Upload Image",
        type=["png", "jpg", "jpeg"],
        help="Supported formats: PNG, JPG, JPEG. Max recommended size: 5MB.",
    )

    if uploaded:
        img = Image.open(uploaded).convert("RGB")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.image(img, caption="📷 Input Image", use_container_width=True)

        with st.spinner("Running PatchCore inference..."):
            try:
                import requests

                img_bytes = io.BytesIO()
                img.save(img_bytes, format="PNG")
                img_bytes.seek(0)

                response = requests.post(
                    f"{VISION_API_URL}/predict",
                    files={"file": (uploaded.name, img_bytes, "image/png")},
                    timeout=120,
                )
                response.raise_for_status()
                result = response.json()
                score = result["score"]
                is_anom = score >= threshold
                inf_ms = result.get("inference_ms", 0)

            except Exception as e:
                st.error(
                    f"❌ **Vision Engine Error**\n\n"
                    f"Could not connect to `{VISION_API_URL}`.\n\n"
                    f"Error: `{e}`\n\n"
                    f"Please ensure the Vision Engine container is running."
                )
                return

        # ── Heatmap ──
        with col2:
            heatmap_b64 = result.get("heatmap_b64")
            if heatmap_b64:
                heatmap_bytes = base64.b64decode(heatmap_b64)
                heatmap_img = Image.open(io.BytesIO(heatmap_bytes))
                st.image(
                    heatmap_img, caption="🔥 Anomaly Heatmap",
                    use_container_width=True,
                )
            else:
                st.warning("No heatmap returned from the API.")

        # ── Result Summary ──
        with col3:
            st.subheader("🔍 Inspection Result")
            if is_anom:
                st.error(f"🚨 **ANOMALY DETECTED**\n\nScore: `{score:.4f}`")
            else:
                st.success(f"✅ **NORMAL**\n\nScore: `{score:.4f}`")

            st.metric(
                label="Anomaly Score",
                value=f"{score:.4f}",
                delta=f"{score - threshold:.4f} vs threshold",
                help="Difference between the anomaly score and the detection threshold.",
            )
            st.caption(f"⏱ Inference time: {inf_ms:.1f} ms")

            with st.expander("📊 Full API Response"):
                display_result = {
                    k: v for k, v in result.items() if k != "heatmap_b64"
                }
                st.json(display_result)


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 3: Analytics & KPIs
# ═══════════════════════════════════════════════════════════════════════════════

def _render_analytics():
    """
    Render the Quality Control & Business Intelligence dashboard.
    Displays KPIs, time-series charts, severity distributions, and
    a gallery of the most critical defects for root-cause investigation.
    """
    st.markdown("### 📈 Quality Control & Business Intelligence")
    st.markdown(
        "Real-time defect analytics, KPIs, and root-cause investigation "
        "powered by PostgreSQL defect logs."
    )

    df = load_defect_logs()

    if df.empty:
        st.info(
            "🎉 **No defects logged yet.** The production line appears to be "
            "running smoothly, or the Vision Engine has not yet processed any images."
        )
        return

    # ── Business KPIs ──
    total_defects = len(df)
    avg_score = df["anomaly_score"].mean()
    max_score = df["anomaly_score"].max()

    last_24h = datetime.datetime.now() - datetime.timedelta(hours=24)
    try:
        recent_defects = len(df[df["timestamp"] >= last_24h])
    except Exception:
        recent_defects = 0

    # Estimated KPIs (business-centric)
    estimated_scrap_cost = total_defects * 12.50  # ~$12.50 per scrapped part
    first_pass_yield = max(0, 100 - (total_defects * 0.15))  # Estimated FPY %

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "🗑️ Total Scrapped Parts", total_defects,
        help="Total parts flagged as anomalous and removed from the production line.",
    )
    col2.metric(
        "⏰ Defects (Last 24h)", recent_defects,
        delta=f"{recent_defects} recent", delta_color="inverse",
        help="Number of defects detected in the past 24 hours.",
    )
    col3.metric(
        "💰 Est. Scrap Cost", f"${estimated_scrap_cost:,.0f}",
        help="Estimated financial impact at ~$12.50 per scrapped unit.",
    )
    col4.metric(
        "🏆 First Pass Yield", f"{first_pass_yield:.1f}%",
        help="Estimated percentage of parts passing quality inspection on first attempt.",
    )

    st.markdown("---")

    # ── Score KPIs ──
    s1, s2 = st.columns(2)
    s1.metric(
        "📊 Avg Anomaly Score", f"{avg_score:.3f}",
        help="Mean anomaly score across all detected defects.",
    )
    s2.metric(
        "🔴 Max Critical Score", f"{max_score:.3f}",
        help="Highest single anomaly score recorded — indicates worst defect.",
    )

    st.markdown("---")

    # ── Interactive Charts ──
    plotly_theme = get_plotly_theme()

    c1, c2 = st.columns(2)
    with c1:
        df_copy = df.copy()
        df_copy["hour"] = df_copy["timestamp"].dt.floor("h")
        defects_timeline = df_copy.groupby("hour").size().reset_index(name="count")
        fig1 = px.line(
            defects_timeline, x="hour", y="count",
            markers=True, title="📉 Defect Occurrence Over Time",
            line_shape="spline",
            color_discrete_sequence=["#EF4444"],
        )
        fig1.update_layout(**plotly_theme)
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        fig2 = px.histogram(
            df, x="anomaly_score", nbins=20,
            title="📊 Defect Severity Distribution",
            marginal="box",
            color_discrete_sequence=["#42A5F5"],
        )
        fig2.update_layout(**plotly_theme)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # ── Top Critical Defects Gallery ──
    st.subheader("📸 Top Critical Defects (Root Cause Investigation)")

    top_critical = df.sort_values(by="anomaly_score", ascending=False).head(3)
    gallery_cols = st.columns(3)

    for idx, row in enumerate(top_critical.itertuples()):
        with gallery_cols[idx]:
            try:
                if hasattr(row, "image_path") and os.path.exists(row.image_path):
                    img = Image.open(row.image_path)
                    st.image(
                        img,
                        caption=(
                            f"Score: {row.anomaly_score:.3f} | "
                            f"{row.timestamp.strftime('%Y-%m-%d %H:%M')}"
                        ),
                        use_container_width=True,
                    )
                else:
                    st.markdown(
                        f'<div class="kave-feed-placeholder" style="padding:1.5rem;">'
                        f'<div class="icon">🖼️</div>'
                        f'<p style="color:#94A3B8 !important; font-size:0.85rem;">'
                        f'Image not available<br>'
                        f'Score: {row.anomaly_score:.3f}</p></div>',
                        unsafe_allow_html=True,
                    )
            except Exception:
                st.warning(f"Could not load defect image #{idx + 1}")

    st.markdown("---")

    # ── Raw Database View ──
    with st.expander("🗄️ View Raw Defect Logs (PostgreSQL Table)"):
        display_cols = ["id", "timestamp", "filename", "anomaly_score"]
        available_cols = [c for c in display_cols if c in df.columns]
        if available_cols:
            st.dataframe(
                df[available_cols].style.highlight_max(
                    axis=0, subset=["anomaly_score"], color="rgba(239,68,68,0.2)"
                ),
                use_container_width=True,
            )
        else:
            st.dataframe(df, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Main Entry Point (exported for master app.py)
# ═══════════════════════════════════════════════════════════════════════════════

def run_vision():
    """
    Main entry function for the Vision Quality Inspection module.
    Called by the master app.py within the Vision tab.
    Renders three sub-tabs: Live Feed, Upload Inspection, Analytics.
    """
    vision_tab1, vision_tab2, vision_tab3 = st.tabs([
        "🔴 Live Feed",
        "📤 Upload Inspection",
        "📈 Analytics & KPIs",
    ])

    with vision_tab1:
        _render_live_feed()

    with vision_tab2:
        _render_upload_inspection()

    with vision_tab3:
        _render_analytics()
