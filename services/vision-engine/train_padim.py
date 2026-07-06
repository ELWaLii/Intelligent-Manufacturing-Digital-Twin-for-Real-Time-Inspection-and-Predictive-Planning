import os
import glob
import pickle
import numpy as np
import torch
import torch.nn.functional as F
import torchvision.models as tvm
from PIL import Image
from tqdm import tqdm
import albumentations as A
from albumentations.pytorch import ToTensorV2

# Configuration
DATA_DIR = "/app/good_data"
SAVE_PATH = "/app/checkpoints/padim_stats.pkl"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {DEVICE}")

# Transform
TRANSFORM = A.Compose([
    A.Resize(224, 224),
    A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ToTensorV2(),
])

# Backbone
_hooks = {}
def _hook(name):
    def fn(module, inp, out):
        _hooks[name] = out
    return fn

print("Loading backbone...")
backbone = tvm.wide_resnet50_2(weights=tvm.Wide_ResNet50_2_Weights.IMAGENET1K_V1).to(DEVICE).eval()
backbone.layer2.register_forward_hook(_hook("layer2"))
backbone.layer3.register_forward_hook(_hook("layer3"))
POOL = torch.nn.AvgPool2d(kernel_size=3, stride=1, padding=1).to(DEVICE)

# Select random dimensions to keep memory manageable (typical PaDiM)
DIMENSION_SUBSET = 100
np.random.seed(42)
idx = np.random.choice(1536, DIMENSION_SUBSET, replace=False)

def extract_features(tensor):
    with torch.no_grad():
        backbone(tensor)
    p2 = POOL(_hooks["layer2"])                                     # (1, 512, 28, 28)
    p3 = POOL(_hooks["layer3"])                                     # (1, 1024, 14, 14)
    p3_up = F.interpolate(p3, size=p2.shape[-2:], mode="bilinear", align_corners=False)
    combined = torch.cat([p2, p3_up], dim=1)                        # (1, 1536, 28, 28)
    # Subset dimensions
    combined = combined[:, idx, :, :]                               # (1, 100, 28, 28)
    return combined.cpu().numpy()

# Extract features for all images
image_paths = glob.glob(os.path.join(DATA_DIR, "*.png")) + glob.glob(os.path.join(DATA_DIR, "*.jpg"))
print(f"Found {len(image_paths)} training images.")

embeddings_list = []
for path in tqdm(image_paths, desc="Extracting features"):
    img = Image.open(path).convert("RGB")
    tensor = TRANSFORM(image=np.array(img))["image"].unsqueeze(0).to(DEVICE)
    features = extract_features(tensor)
    embeddings_list.append(features)

# embeddings: shape (N, 100, 28, 28)
embeddings = np.concatenate(embeddings_list, axis=0)
N, C, H, W = embeddings.shape
embeddings = embeddings.reshape(N, C, H * W)

print("Calculating PaDiM stats (mean and inverse covariance)...")
mean = np.mean(embeddings, axis=0) # (C, H*W)
cov_inv = np.zeros((C, C, H * W))

I = np.eye(C)
for i in tqdm(range(H * W), desc="Calculating Covariance"):
    cov = np.cov(embeddings[:, :, i], rowvar=False) # shape (C, C)
    cov = cov + 0.01 * I # Add epsilon to make it invertible
    cov_inv[:, :, i] = np.linalg.inv(cov)

os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
with open(SAVE_PATH, "wb") as f:
    pickle.dump({
        "mean": mean,
        "cov_inv": cov_inv,
        "idx": idx,
        "H": H,
        "W": W
    }, f)

print(f"PaDiM training complete! Stats saved to {SAVE_PATH}")
