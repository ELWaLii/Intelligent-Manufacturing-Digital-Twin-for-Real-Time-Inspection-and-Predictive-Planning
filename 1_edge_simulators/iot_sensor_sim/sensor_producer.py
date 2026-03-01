import json
import time
import random
from datetime import datetime

def generate_sensor_data():
    data = {
        "timestamp": datetime.utcnow().isoformat(),
        "machine_id": "M01",
        "temperature": round(random.uniform(60, 80), 2),
        "vibration": round(random.uniform(0.5, 1.5), 2),
        "torque": round(random.uniform(40, 60), 2)
    }
    return data

while True:
    sensor_data = generate_sensor_data()

    # Save data in JSON file
    with open("sensor_stream.json", "a") as f:
        f.write(json.dumps(sensor_data) + "\n")

    print(sensor_data)

    time.sleep(0.1)  # 100 milliseconds
