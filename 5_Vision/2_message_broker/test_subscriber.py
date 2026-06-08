import redis
import json

try:
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    print("Connected to Redis successfully (Subscriber Test)!")
except Exception as e:
    print(f"Connection failed: {e}")
    exit(1)

channel_name = "factory:metal_nut:images"

pubsub = r.pubsub()
pubsub.subscribe(channel_name)

print(f"🎧 Listening for images on channel: '{channel_name}'... (Press Ctrl+C to exit)")

try:
    for message in pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            print("\n [RECEIVED NEW IMAGE IN REAL-TIME]")
            print(f"Image ID  : {data['image_id']}")
            print(f"imestamp : {data['timestamp']}")
            print(f"Base64 Snip: {data['image_base64'][:30]}...") 
except KeyboardInterrupt:
    print("\nStopped listening.")