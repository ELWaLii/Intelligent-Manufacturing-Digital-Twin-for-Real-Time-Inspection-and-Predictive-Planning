import urllib.request
import json
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

req = urllib.request.Request(url)
try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print("Available models supporting generateContent:")
        for model in data.get("models", []):
            methods = model.get("supportedGenerationMethods", [])
            if "generateContent" in methods:
                print(model.get("name"))
except Exception as e:
    print(f"Error fetching models: {e}")
