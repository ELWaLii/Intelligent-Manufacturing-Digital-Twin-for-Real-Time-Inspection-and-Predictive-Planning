"""
Streamlit UI — Metal Nut Anomaly Detection
Run: streamlit run streamlit_app.py
"""
import streamlit as st
from PIL import Image
import io, requests, base64

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Metal Nut Anomaly Detector", page_icon="🔩", layout="wide")
st.title("🔩 Metal Nut Anomaly Detection")
st.markdown("Upload an image of a metal nut to detect anomalies using **PatchCore**.")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Model Info")

    try:
        cfg = requests.get(f"{API_URL}/config", timeout=3).json()
        real_threshold = float(cfg.get("threshold", 0.5))
        st.success(f"✅ API Connected\nThreshold: {real_threshold:.4f}")
        st.info(f"**Model**: {cfg.get('model','PatchCore')}\n"
                f"**Backbone**: WideResNet-50-2\n"
                f"**Task**: Unsupervised Anomaly Detection")
    except Exception:
        real_threshold = 0.5
        st.error("⚠️ API not reachable!\nRun:\n`uvicorn app:app --reload`")

    threshold = st.slider("Override Threshold", 0.0, 5.0, real_threshold, 0.01)

# ── Upload ─────────────────────────────────────────────────────────────────────
uploaded = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"])

if uploaded:
    img = Image.open(uploaded).convert("RGB")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.image(img, caption="Input Image", use_container_width=True)

    with st.spinner("Running inference..."):
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        try:
            response = requests.post(
                f"{API_URL}/predict",
                files={"file": (uploaded.name, img_bytes, "image/png")},
                timeout=120,
            )
            response.raise_for_status()
            result  = response.json()
            score   = result["score"]
            is_anom = score >= threshold
            inf_ms  = result.get("inference_ms", 0)

        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to FastAPI!\nRun: `uvicorn app:app --reload`")
            st.stop()
        except Exception as e:
            st.error(f"❌ API Error: {e}")
            st.stop()

    # ✅ Real heatmap من الـ API
    with col2:
        heatmap_b64 = result.get("heatmap_b64")
        if heatmap_b64:
            heatmap_bytes = base64.b64decode(heatmap_b64)
            heatmap_img   = Image.open(io.BytesIO(heatmap_bytes))
            st.image(heatmap_img, caption="Anomaly Heatmap", use_container_width=True)
        else:
            st.warning("No heatmap returned from API")

    with col3:
        st.subheader("🔍 Result")
        if is_anom:
            st.error(f"🚨 **ANOMALY DETECTED**\n\nScore: `{score:.4f}`")
        else:
            st.success(f"✅ **NORMAL**\n\nScore: `{score:.4f}`")

        st.metric(
            label="Anomaly Score",
            value=f"{score:.4f}",
            delta=f"{score - threshold:.4f} vs threshold",
        )
        st.caption(f"⏱ Inference time: {inf_ms:.1f} ms")

        with st.expander("📊 Full API Response"):
            display_result = {k: v for k, v in result.items() if k != "heatmap_b64"}
            st.json(display_result)