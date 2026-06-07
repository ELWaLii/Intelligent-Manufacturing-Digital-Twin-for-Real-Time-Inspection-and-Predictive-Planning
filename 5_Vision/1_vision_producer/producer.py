import os
import time
import base64
import cv2
from redis import Redis

redis_client = Redis(host='localhost', port=6379, db=0)

IMAGE_DIR = 'sample_image'
FRAME_RATE = 1 / 30.0  

def stream_images():
    while True:
        
        images = [f for f in os.listdir(IMAGE_DIR) if f != '.gitkeep']
        if not images:
            print("The folder is empty! Waiting for pictures...")
            time.sleep(2)
            continue
            
        for img_name in images:
            img_path = os.path.join(IMAGE_DIR, img_name)
            
           
            with open(img_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
            
            redis_client.xadd('image_stream', {'image': encoded_string, 'filename': img_name})
            
          
            time.sleep(FRAME_RATE)

if __name__ == "__main__":
    stream_images()