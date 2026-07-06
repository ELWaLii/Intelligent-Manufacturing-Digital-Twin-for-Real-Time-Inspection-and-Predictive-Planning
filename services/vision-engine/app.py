"""
KAVE Vision Engine — Hybrid AI Inference Service
==================================================
Combined FastAPI REST API + Redis Streams consumer for PatchCore
anomaly detection on metal nut images.

Architecture:
  - FastAPI /predict endpoint for on-demand single-image inference
  - Background Redis consumer thread for real-time edge camera stream
  - PostgreSQL logging for all detected anomalies
  - Shared defects archive volume for image persistence

Model: PatchCore with WideResNet-50-2 backbone
  - Multi-layer feature extraction (layer2 + layer3 hooks)
  - Memory bank KNN distance scoring
  - Real-time heatmap generation

Author: KAVE Engineering Team
Version: 2.0.0
"""

import os
import io
import json
import time
import base64
import datetime
import threading
import asyncio
import pickle

import numpy as np
import cv2
import torch
import torch.nn.functional as F
import torchvision.models as tvm
import albumentations as A
from albumentations.pytorch import ToTensorV2
from sklearn.neighbors import NearestNeighbors
from PIL import Image
from redis import Redis
import psycopg2

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import uvicorn


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Configuration & Model Loading
# ═══════════════════════════════════════════════════════════════════════════════

print("⚙️ [Vision Engine] Loading configuration and AI assets...")

# Paths — check both flat and nested directory structures
EXPORTS_DIR = "./exports"
CHECKPOINTS_DIR = "./checkpoints"

CFG_PATH = os.path.join(EXPORTS_DIR, "inference_config.json")
if not os.path.exists(CFG_PATH):
    CFG_PATH = "inference_config.json"

BANK_PATH = os.path.join(CHECKPOINTS_DIR, "patchcore_memory_bank.npy")
if not os.path.exists(BANK_PATH):
    BANK_PATH = "patchcore_memory_bank.npy"

# Load config
try:
    with open(CFG_PATH, encoding="utf-8") as f:
        CFG = json.load(f)
    print(f"[Vision Engine] Config loaded from: {CFG_PATH}")
except FileNotFoundError:
    CFG = {
        "model": "PatchCore",
        "backbone": "wide_resnet50_2",
        "image_size": 256,
        "crop_size": 224,
        "imagenet_mean": [0.485, 0.456, 0.406],
        "imagenet_std": [0.229, 0.224, 0.225],
        "threshold": 0.5,
    }
    print("[Vision Engine] WARNING: Using default config (inference_config.json not found)")

# Defects archive directory
DEFECTS_DIR = os.environ.get("DEFECTS_DIR", "defects_archive")
os.makedirs(DEFECTS_DIR, exist_ok=True)

# Device selection
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"🖥️ [Vision Engine] Using device: {DEVICE}")
if DEVICE.type == "cuda":
    torch.backends.cudnn.benchmark = True
else:
    num_threads = max(1, (os.cpu_count() or 2) - 1)
    torch.set_num_threads(num_threads)
    print(f"🖥️ [Vision Engine] CPU optimized: using {num_threads} threads")

# ── Backbone (WideResNet50-2 with multi-layer hooks) ──────────────────────────
_hooks = {}


def _hook(name):
    """Register a forward hook to capture intermediate layer activations.

    Args:
        name (str): The name of the layer to capture (e.g., 'layer2').

    Returns:
        Callable: The hook function to be registered with the PyTorch module.
    """
    def fn(module, inp, out):
        _hooks[name] = out
    return fn


try:
    backbone = tvm.wide_resnet50_2(weights=tvm.Wide_ResNet50_2_Weights.IMAGENET1K_V1)
    backbone = backbone.to(DEVICE).eval()
    backbone.layer2.register_forward_hook(_hook("layer2"))
    backbone.layer3.register_forward_hook(_hook("layer3"))
    POOL = torch.nn.AvgPool2d(kernel_size=3, stride=1, padding=1).to(DEVICE)
    print("[Vision Engine] ✅ Backbone (WideResNet-50-2) loaded with layer2+layer3 hooks")
except Exception as e:
    backbone = None
    POOL = None
    print(f"[Vision Engine] ⚠️ Could not load backbone: {e}")

# ── Memory Bank + KNN ─────────────────────────────────────────────────────────
try:
    MEMORY_BANK = np.load(BANK_PATH)
    
    # Drastic coreset reduction for sub-second inference (1%)
    coreset_ratio = 0.01
    num_samples = max(1, int(MEMORY_BANK.shape[0] * coreset_ratio))
    np.random.seed(42) # For consistency
    indices = np.random.choice(MEMORY_BANK.shape[0], num_samples, replace=False)
    MEMORY_BANK = MEMORY_BANK[indices]

    KNN = NearestNeighbors(
        n_neighbors=10, metric="euclidean", algorithm="ball_tree", n_jobs=-1
    )
    KNN.fit(MEMORY_BANK)
    print(f"[Vision Engine] ✅ Memory bank loaded: {MEMORY_BANK.shape}")
except Exception as e:
    MEMORY_BANK = None
    KNN = None
    print(f"[Vision Engine] ⚠️ Could not load memory bank: {e}")

# ── PaDiM Stats ───────────────────────────────────────────────────────────────
PADIM_PATH = os.path.join(CHECKPOINTS_DIR, "padim_stats.pkl")
if not os.path.exists(PADIM_PATH):
    PADIM_PATH = "padim_stats.pkl"
try:
    with open(PADIM_PATH, "rb") as f:
        PADIM_STATS = pickle.load(f)
    print(f"[Vision Engine] ✅ PaDiM stats loaded. Dim subset: {len(PADIM_STATS['idx'])}")
except Exception as e:
    PADIM_STATS = None
    print(f"[Vision Engine] ⚠️ Could not load PaDiM stats: {e}")

# ── Preprocessing Transform ───────────────────────────────────────────────────
TRANSFORM = A.Compose([
    # Strictly enforce 224x224 resolution limit
    A.Resize(224, 224),
    A.Normalize(mean=CFG["imagenet_mean"], std=CFG["imagenet_std"]),
    ToTensorV2(),
])


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Database & Redis Connections
# ═══════════════════════════════════════════════════════════════════════════════

def get_db_connection():
    """Create a new PostgreSQL connection for defect logging.

    Returns:
        psycopg2.extensions.connection: A connection object to the PostgreSQL database,
            or None if the connection fails.
    """
    try:
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "kave_db"),
            port=int(os.environ.get("DB_PORT", 5432)),
            database=os.environ.get("POSTGRES_DB", "kave_db"),
            user=os.environ.get("POSTGRES_USER", "admin"),
            password=os.environ.get("POSTGRES_PASSWORD", "kave_pass"),
        )
        return conn
    except Exception as e:
        print(f"❌ [Vision Engine] Database connection failed: {e}")
        return None


def _init_defect_table():
    """Create the defect_logs table if it doesn't exist.
    
    This function initializes the PostgreSQL table used for storing anomaly logs.
    """
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS defect_logs (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP,
                        filename VARCHAR(255),
                        anomaly_score FLOAT,
                        image_path TEXT
                    )
                """)
                conn.commit()
            print("[Vision Engine] ✅ PostgreSQL 'defect_logs' table ready.")
        except Exception as e:
            print(f"[Vision Engine] DB table init error: {e}")
        finally:
            conn.close()


# Initialize table at module load
_init_defect_table()

# Redis client
REDIS_HOST = os.environ.get("REDIS_HOST", "kave_redis")
IN_STREAM = "image_stream"
OUT_STREAM = "results_stream"


def _get_redis_client():
    """Create a Redis client with error handling.

    Returns:
        Redis: A connected Redis client instance, or None if the connection fails.
    """
    try:
        client = Redis(host=REDIS_HOST, port=6379, db=0, socket_timeout=5)
        client.ping()
        return client
    except Exception as e:
        print(f"[Vision Engine] Redis connection failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Core Inference Functions
# ═══════════════════════════════════════════════════════════════════════════════

def extract_features(tensor: torch.Tensor):
    """
    Extract multi-scale patch features from the backbone.
    Uses layer2 (512-dim) + layer3 (1024-dim) = 1536-dim combined features.

    Args:
        tensor: Input image tensor of shape (1, 3, H, W).

    Returns:
        tuple: (patches, feature_H, feature_W)
            - patches: numpy array of shape (H*W, 1536)
            - feature_H, feature_W: spatial dimensions of the feature maps
    """
    with torch.no_grad():
        backbone(tensor)

    p2 = POOL(_hooks["layer2"])                                     # (1, 512, 28, 28)
    p3 = POOL(_hooks["layer3"])                                     # (1, 1024, 14, 14)
    p3_up = F.interpolate(
        p3, size=p2.shape[-2:], mode="bilinear", align_corners=False
    )                                                               # (1, 1024, 28, 28)
    combined = torch.cat([p2, p3_up], dim=1)                        # (1, 1536, 28, 28)

    B, C, H, W = combined.shape
    combined_np = combined.cpu().numpy()
    patches = combined.permute(0, 2, 3, 1).reshape(-1, C).cpu().numpy()
    return patches, combined_np, H, W


def make_heatmap(patches: np.ndarray, fH: int, fW: int, out_size: int = 224) -> np.ndarray:
    """
    Generate an anomaly heatmap from patch-level KNN distances.

    Args:
        patches: Patch feature vectors.
        fH, fW: Feature map spatial dimensions.
        out_size: Output heatmap resolution.

    Returns:
        np.ndarray: Normalized score map (0-1) of shape (out_size, out_size).
    """
    distances, _ = KNN.kneighbors(patches)
    patch_scores = distances.mean(axis=1)
    score_map = patch_scores.reshape(fH, fW)

    s_min, s_max = score_map.min(), score_map.max()
    if s_max > s_min:
        score_map = (score_map - s_min) / (s_max - s_min)

    score_map_up = cv2.resize(
        score_map.astype(np.float32), (out_size, out_size),
        interpolation=cv2.INTER_LINEAR,
    )
    return score_map_up


def heatmap_to_b64(score_map: np.ndarray) -> str:
    """Convert a normalized score map to a base64-encoded PNG image.

    Args:
        score_map (np.ndarray): Normalized score map (0-1) of the anomaly heatmap.

    Returns:
        str: A base64-encoded string representing the PNG image of the heatmap.
    """
    img_uint8 = (score_map * 255).astype(np.uint8)
    colored = cv2.applyColorMap(img_uint8, cv2.COLORMAP_JET)
    colored_rgb = cv2.cvtColor(colored, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(colored_rgb)
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def make_heatmap_padim(features: np.ndarray, fH: int, fW: int, out_size: int = 224):
    """Generate anomaly heatmap using PaDiM Mahalanobis distance."""
    features_subset = features[:, PADIM_STATS["idx"], :, :] # (1, 100, 28, 28)
    C = features_subset.shape[1]
    features_subset = features_subset.reshape(C, fH * fW) # (100, 784)
    
    mean = PADIM_STATS["mean"] # (100, 784)
    cov_inv = PADIM_STATS["cov_inv"] # (100, 100, 784)
    
    distances = np.zeros(fH * fW)
    for i in range(fH * fW):
        diff = features_subset[:, i] - mean[:, i]
        dist = np.sqrt(np.dot(np.dot(diff.T, cov_inv[:, :, i]), diff))
        distances[i] = dist
        
    score_map = distances.reshape(fH, fW)
    score = float(distances.max())
    
    s_min, s_max = score_map.min(), score_map.max()
    if s_max > s_min:
        score_map = (score_map - s_min) / (s_max - s_min)
        
    score_map_up = cv2.resize(
        score_map.astype(np.float32), (out_size, out_size),
        interpolation=cv2.INTER_LINEAR,
    )
    return score_map_up, score


def process_image_patchcore(img_rgb: np.ndarray):
    """Run PatchCore inference on a single image (Manual Uploads)."""
    t0 = time.time()
    tensor = TRANSFORM(image=img_rgb)["image"].unsqueeze(0).to(DEVICE)

    patches, _, fH, fW = extract_features(tensor)
    distances, _ = KNN.kneighbors(patches)
    patch_scores = distances.mean(axis=1)
    score = float(patch_scores.max())

    score_map = make_heatmap(patches, fH, fW, out_size=224)
    hm_b64 = heatmap_to_b64(score_map)

    inf_time = (time.time() - t0) * 1000
    return score, hm_b64, inf_time


def process_image_padim(img_rgb: np.ndarray):
    """Run fast PaDiM inference on a single image (Real-time Stream)."""
    t0 = time.time()
    tensor = TRANSFORM(image=img_rgb)["image"].unsqueeze(0).to(DEVICE)

    _, combined_np, fH, fW = extract_features(tensor)
    
    score_map, score = make_heatmap_padim(combined_np, fH, fW, out_size=224)
    hm_b64 = heatmap_to_b64(score_map)

    inf_time = (time.time() - t0) * 1000
    return score, hm_b64, inf_time


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Redis Background Consumer Worker
# ═══════════════════════════════════════════════════════════════════════════════

def redis_consumer_worker():
    """
    Background thread that reads from the Redis 'image_stream',
    runs inference, logs anomalies to PostgreSQL, and publishes
    results to 'results_stream' for the Streamlit live feed.
    """
    redis_client = _get_redis_client()
    if redis_client is None:
        print("[Vision Engine] ❌ Redis consumer could not start — no connection.")
        return

    print(f"🎧 [Vision Engine] Redis consumer started! Listening on '{IN_STREAM}'...")
    last_id = "$"

    while True:
        try:
            # Read up to 100 pending messages
            messages = redis_client.xread({IN_STREAM: last_id}, count=100, block=0)

            for stream, message_list in messages:
                if not message_list:
                    continue

                if len(message_list) > 1:
                    print(f"⚠️ [Vision Engine] Dropping {len(message_list) - 1} stale frames. Real-time processing active.")
                    # Update last_id for dropped messages
                    for msg_id, _ in message_list[:-1]:
                        last_id = msg_id

                # Only run the heavy inference loop on the very last message
                for message_id, message_data in message_list[-1:]:
                    last_id = message_id

                    filename = message_data[b"filename"].decode("utf-8")
                    img_bytes = base64.b64decode(
                        message_data[b"image"].decode("utf-8")
                    )
                    np_arr = np.frombuffer(img_bytes, np.uint8)
                    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

                    # Run inference (PaDiM for stream)
                    score, hm_b64, inf_time = process_image_padim(img_rgb)
                    is_anomaly = score >= CFG["threshold"]
                    label = "ANOMALY" if is_anomaly else "NORMAL"

                    # Log anomalies to PostgreSQL
                    if is_anomaly:
                        try:
                            conn = get_db_connection()
                            if conn:
                                # Save overlay image
                                hm_bytes = base64.b64decode(hm_b64)
                                hm_img = cv2.imdecode(
                                    np.frombuffer(hm_bytes, np.uint8),
                                    cv2.IMREAD_COLOR,
                                )
                                img_resized = cv2.resize(img_rgb, (224, 224))
                                img_bgr_resized = cv2.cvtColor(img_resized, cv2.COLOR_RGB2BGR)
                                overlay = cv2.addWeighted(
                                    img_bgr_resized, 0.5, hm_img, 0.5, 0
                                )

                                ts = datetime.datetime.now()
                                save_path = os.path.join(
                                    DEFECTS_DIR,
                                    f"defect_{ts.strftime('%Y%m%d_%H%M%S_%f')}_{filename}",
                                )
                                cv2.imwrite(save_path, overlay)

                                with conn.cursor() as cur:
                                    cur.execute(
                                        "INSERT INTO defect_logs "
                                        "(timestamp, filename, anomaly_score, image_path) "
                                        "VALUES (%s, %s, %s, %s)",
                                        (ts, filename, score, save_path),
                                    )
                                    conn.commit()
                                conn.close()
                        except Exception as db_err:
                            print(f"❌ [Vision Engine] DB write error: {db_err}")

                    # Publish to output stream for Streamlit
                    result_payload = {
                        "filename": filename,
                        "score": str(round(score, 4)),
                        "is_anomaly": str(int(is_anomaly)),
                        "label": label,
                        "inference_ms": str(round(inf_time, 2)),
                        "heatmap_b64": hm_b64,
                        "original_b64": message_data[b"image"].decode("utf-8"),
                    }
                    redis_client.xadd(OUT_STREAM, result_payload, maxlen=100, approximate=True)

                    print(
                        f"[{label}] {filename} | "
                        f"Score: {score:.4f} | {inf_time:.1f}ms"
                    )

        except Exception as e:
            print(f"❌ [Vision Engine] Redis consumer error: {e}")
            time.sleep(2)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. FastAPI Application
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="KAVE Vision Engine API",
    description="PatchCore anomaly detection — Metal Nut inspection",
    version="2.0.0",
)


@app.on_event("startup")
def startup_event():
    """Start the Redis consumer worker in a background daemon thread."""
    worker = threading.Thread(target=redis_consumer_worker, daemon=True)
    worker.start()
    print("[Vision Engine] ✅ FastAPI started | Redis consumer thread launched")


@app.get("/", summary="Health check")
def health_check():
    """Return system health status."""
    return {
        "status": "Active",
        "model": "PatchCore (WideResNet-50-2)",
        "device": str(DEVICE),
        "architecture": "Hybrid (FastAPI + Redis Streams)",
    }


@app.get("/health", summary="Detailed health check")
def detailed_health():
    """Return health status for container orchestration.
    Returns {"status": "ok"} with 200 to satisfy Docker healthcheck."""
    return {
        "status": "ok",
        "backbone_loaded": backbone is not None,
        "memory_bank_loaded": MEMORY_BANK is not None,
        "device": str(DEVICE),
    }


@app.get("/config", summary="Return model configuration")
def get_config():
    """Return the current inference configuration."""
    return CFG


@app.post("/predict", summary="Predict anomaly + heatmap")
async def predict(file: UploadFile = File(...)):
    """
    Run PatchCore inference on an uploaded image.

    Returns JSON with: filename, score, is_anomaly, label,
    threshold, inference_ms, heatmap_b64.
    """
    if not file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        raise HTTPException(400, "Only PNG/JPG images accepted")

    if backbone is None or KNN is None:
        raise HTTPException(503, "Model not loaded — check server logs")

    try:
        contents = await file.read()
        img = np.array(Image.open(io.BytesIO(contents)).convert("RGB"))

        # Run inference in a background thread to prevent blocking the event loop
        score, hm_b64, inf_time = await asyncio.to_thread(process_image_patchcore, img)

        return JSONResponse({
            "filename": file.filename,
            "score": round(score, 6),
            "is_anomaly": bool(score >= CFG["threshold"]),
            "label": "ANOMALY" if score >= CFG["threshold"] else "NORMAL",
            "threshold": CFG["threshold"],
            "inference_ms": round(inf_time, 2),
            "heatmap_b64": hm_b64,
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Entrypoint
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
