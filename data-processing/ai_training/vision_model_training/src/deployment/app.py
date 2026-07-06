"""
FastAPI Deployment — Metal Nut Anomaly Detection
Run: uvicorn app:app --host 0.0.0.0 --port 8000 --reload
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import numpy as np, io, json, time, os, base64
from PIL import Image
import torch
import torch.nn.functional as F
import torchvision.models as tvm
import albumentations as A
from albumentations.pytorch import ToTensorV2
from sklearn.neighbors import NearestNeighbors
import cv2

# ── Paths ──────────────────────────────────────────────────────────────────────
EXPORTS  = "./exports"
CHECKPTS = "./checkpoints"

CFG_PATH  = os.path.join(EXPORTS,  "inference_config.json")
BANK_PATH = os.path.join(CHECKPTS, "patchcore_memory_bank.npy")

print(f"[INFO] CFG  : {CFG_PATH}")
print(f"[INFO] BANK : {BANK_PATH}")

# ── Config ─────────────────────────────────────────────────────────────────────
with open(CFG_PATH, encoding="utf-8") as f:
    CFG = json.load(f)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[INFO] Device: {DEVICE}")

# ── Backbone (WideResNet50-2) ──────────────────────────────────────────────────
backbone = tvm.wide_resnet50_2(weights=tvm.Wide_ResNet50_2_Weights.IMAGENET1K_V1)
backbone = backbone.to(DEVICE).eval()

# Hook على layer2 و layer3
_hooks = {}

def _hook(name):
    def fn(module, inp, out):
        _hooks[name] = out
    return fn

backbone.layer2.register_forward_hook(_hook("layer2"))
backbone.layer3.register_forward_hook(_hook("layer3"))

POOL = torch.nn.AvgPool2d(kernel_size=3, stride=1, padding=1).to(DEVICE)

print("[INFO] Backbone ready ✅")

# ── Memory Bank + KNN ─────────────────────────────────────────────────────────
MEMORY_BANK = np.load(BANK_PATH)
KNN = NearestNeighbors(n_neighbors=10, metric="euclidean", algorithm="ball_tree", n_jobs=-1)
KNN.fit(MEMORY_BANK)
print(f"[INFO] Memory bank: {MEMORY_BANK.shape} ✅")

# ── Transform ─────────────────────────────────────────────────────────────────
TRANSFORM = A.Compose([
    A.Resize(CFG["image_size"], CFG["image_size"]),
    A.CenterCrop(CFG["crop_size"], CFG["crop_size"]),
    A.Normalize(mean=CFG["imagenet_mean"], std=CFG["imagenet_std"]),
    ToTensorV2(),
])

# ── Feature extraction ────────────────────────────────────────────────────────
def extract_features(tensor: torch.Tensor):
    """
    tensor: (1, 3, H, W) على الـ device
    return: (784, 1536) patch features
    """
    with torch.no_grad():
        backbone(tensor)

    p2 = POOL(_hooks["layer2"])                                          # (1, 512,  28, 28)
    p3 = POOL(_hooks["layer3"])                                          # (1, 1024, 14, 14)
    p3_up = F.interpolate(p3, size=p2.shape[-2:],
                          mode="bilinear", align_corners=False)          # (1, 1024, 28, 28)
    combined = torch.cat([p2, p3_up], dim=1)                            # (1, 1536, 28, 28)

    B, C, H, W = combined.shape
    patches = combined.permute(0, 2, 3, 1).reshape(-1, C).cpu().numpy() # (784, 1536)
    return patches, H, W

# ── Heatmap ───────────────────────────────────────────────────────────────────
def make_heatmap(patches: np.ndarray, fH: int, fW: int, out_size: int = 224) -> np.ndarray:
    distances, _ = KNN.kneighbors(patches)        # (784, 10)
    patch_scores  = distances.mean(axis=1)         # (784,)
    score_map     = patch_scores.reshape(fH, fW)   # (28, 28)

    s_min, s_max = score_map.min(), score_map.max()
    if s_max > s_min:
        score_map = (score_map - s_min) / (s_max - s_min)

    score_map_up = cv2.resize(score_map.astype(np.float32),
                              (out_size, out_size),
                              interpolation=cv2.INTER_LINEAR)
    return score_map_up

def heatmap_to_b64(score_map: np.ndarray) -> str:
    img_uint8   = (score_map * 255).astype(np.uint8)
    colored     = cv2.applyColorMap(img_uint8, cv2.COLORMAP_JET)
    colored_rgb = cv2.cvtColor(colored, cv2.COLOR_BGR2RGB)
    pil_img     = Image.fromarray(colored_rgb)
    buf         = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Metal Nut Anomaly Detection API",
    description="MVTec AD — PatchCore inference endpoint",
    version="3.0.0",
)

@app.get("/", summary="Health check")
def root():
    return {"status": "ok", "model": "PatchCore", "device": DEVICE}

@app.post("/predict", summary="Predict anomaly + real heatmap")
async def predict(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        raise HTTPException(400, "Only PNG/JPG images accepted")

    t0 = time.time()

    # Preprocess
    img    = np.array(Image.open(io.BytesIO(await file.read())).convert("RGB"))
    tensor = TRANSFORM(image=img)["image"].unsqueeze(0).to(DEVICE)

    # Extract patch features
    patches, fH, fW = extract_features(tensor)

    # Image-level score = max patch score (PatchCore standard)
    distances, _ = KNN.kneighbors(patches)
    patch_scores  = distances.mean(axis=1)
    score         = float(patch_scores.max())

    # Real heatmap
    score_map   = make_heatmap(patches, fH, fW, out_size=224)
    heatmap_b64 = heatmap_to_b64(score_map)

    elapsed = (time.time() - t0) * 1000

    return JSONResponse({
        "filename"    : file.filename,
        "score"       : round(score, 6),
        "is_anomaly"  : bool(score >= CFG["threshold"]),
        "label"       : "ANOMALY" if score >= CFG["threshold"] else "NORMAL",
        "threshold"   : CFG["threshold"],
        "inference_ms": round(elapsed, 2),
        "heatmap_b64" : heatmap_b64,
    })

@app.get("/config", summary="Return model configuration")
def get_config():
    return CFG