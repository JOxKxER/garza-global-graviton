import os
import requests

api_key = os.getenv("GEMINI_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

payload = {
    "contents": [
        {
            "parts": [
                {"text": "Explain how AI works in a few words"}
            ]
        }
    ]
}

response = requests.post(url, json=payload)
if response.status_code == 200:
    result = response.json()
    print("Gemini Response:", result["candidates"][0]["content"]["parts"][0]["text"])
else:
    print(f"Error: {response.text}")
