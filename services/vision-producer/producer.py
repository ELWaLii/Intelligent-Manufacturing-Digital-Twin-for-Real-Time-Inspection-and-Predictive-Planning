"""
KAVE Vision Producer — Edge Camera Simulator
==============================================
Simulates an edge camera by reading images from a directory and
streaming them to Redis for real-time AI inspection.

Environment Variables:
    REDIS_HOST: Redis server hostname (default: kave_redis)

Author: KAVE Engineering Team
Version: 2.0.0
"""

import os
import time
import base64
import cv2
import numpy as np
from redis import Redis

# ── Configuration ──────────────────────────────────────────────────────────────
REDIS_HOST = os.environ.get("REDIS_HOST", "kave_redis")
IMAGE_DIR = "sample_image"       # Directory containing test images
FRAME_RATE = 1 / 30.0           # Simulated camera speed (30 FPS)
STREAM_NAME = "image_stream"
MAX_STREAM_LEN = 1000           # Keep last 1000 frames in Redis

# ── Redis Connection with Retry ────────────────────────────────────────────────
MAX_RETRIES = 10
RETRY_DELAY = 3


def connect_redis() -> Redis:
    """Connect to Redis with retry logic for container startup delays.

    Returns:
        Redis: A connected Redis client instance.

    Raises:
        ConnectionError: If the connection cannot be established after MAX_RETRIES.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            client = Redis(host=REDIS_HOST, port=6379, db=0, socket_timeout=5)
            client.ping()
            print(f"✅ Connected to Redis at {REDIS_HOST}:6379")
            return client
        except Exception as e:
            print(
                f"⏳ Redis connection attempt {attempt}/{MAX_RETRIES} failed: {e}. "
                f"Retrying in {RETRY_DELAY}s..."
            )
            time.sleep(RETRY_DELAY)

    raise ConnectionError(f"Could not connect to Redis after {MAX_RETRIES} attempts.")


# ── Main Streaming Function ───────────────────────────────────────────────────
def stream_images():
    """Continuously stream images from IMAGE_DIR to Redis.
    
    Each image is Base64-encoded and published to 'image_stream'
    for consumption by the Vision Engine. The images are sent at a rate
    defined by FRAME_RATE.
    """
    print(f"🎥 [Vision Producer] Starting... Streaming from '{IMAGE_DIR}'")

    # Create directory if it doesn't exist
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)
        print(f"⚠️ Created missing folder '{IMAGE_DIR}'. Add images to start streaming.")
        return

    redis_client = connect_redis()

    while True:
        # Read all image files, ignoring hidden files
        images = sorted([
            f for f in os.listdir(IMAGE_DIR)
            if f != ".gitkeep" and not f.startswith(".")
            and f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))
        ])

        if not images:
            print("⏳ No images found in folder. Waiting...")
            time.sleep(2)
            continue

        frame_count = 0
        for img_name in images:
            frame_count += 1
            if frame_count % 3 != 0:
                continue

            img_path = os.path.join(IMAGE_DIR, img_name)

            try:
                # Read, resize, and encode the image
                img_bgr = cv2.imread(img_path)
                if img_bgr is None:
                    continue
                img_resized = cv2.resize(img_bgr, (224, 224))
                _, buffer = cv2.imencode('.jpg', img_resized, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                encoded_string = base64.b64encode(buffer).decode("utf-8")

                redis_client.xadd(
                    STREAM_NAME,
                    {"image": encoded_string, "filename": img_name},
                    maxlen=MAX_STREAM_LEN,
                    approximate=True
                )

                print(f"📤 Sent to Redis (Skipped 2, Resized): {img_name}")

            except Exception as e:
                print(f"❌ Error reading {img_name}: {e}")

            time.sleep(FRAME_RATE * 3)


if __name__ == "__main__":
    try:
        stream_images()
    except KeyboardInterrupt:
        print("\n🛑 Vision Producer stopped.")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
