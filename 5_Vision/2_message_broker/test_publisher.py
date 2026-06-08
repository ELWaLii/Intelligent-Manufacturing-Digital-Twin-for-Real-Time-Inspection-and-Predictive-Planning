import redis
import json
import time

try:
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    print("Connected to Redis successfully (Publisher Test)!")
except Exception as e:
    print(f"Connection failed: {e}")
    exit(1)

channel_name = "factory:metal_nut:images"
print(f"Simulation started. Publishing to channel: '{channel_name}'\n")

for i in range(1, 6):
    payload = {
        "image_id": f"nut_{i:04d}",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "image_base64": f"iVBORw0KGgoAAAANSUhEUgAA...[FAKE_BASE64_FOR_NUT_{i}]..."
    }
    
    json_payload = json.dumps(payload)
    
    r.publish(channel_name, json_payload)
    print(f"📤 [SENT] Published: {payload['image_id']}")
    
    time.sleep(2) 

print("\n🏁 Finished publishing test data.")