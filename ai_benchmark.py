"""
Garza Global Graviton Core Module
Automated Vault Infrastructure Script
"""
import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_PATH = os.path.join(BASE_DIR, "04_Legal_and_IP", "sovereign_ledger.json")
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"

def run_benchmark():
    """Dispatches a test payload to LM Studio and measures round-trip latency."""
    payload = {
        "messages": [
            {"role": "user", "content": "Return the phrase 'LOCAL_AI_ONLINE' and nothing else."}
        ],
        "temperature": 0.1,
        "max_tokens": 20
    }
    
    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(LM_STUDIO_URL, data=data, headers=headers, method="POST")
    
    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            elapsed = round(time.time() - start_time, 3)
            res_body = json.loads(response.read().decode("utf-8"))
            content = res_body["choices"][0]["message"]["content"].strip()
            return True, elapsed, content
    except urllib.error.URLError as e:
        return False, 0.0, f"Endpoint Offline / Timeout: {e.reason}"
    except Exception as e:
        return False, 0.0, f"Error: {str(e)}"

def log_benchmark_event(success, latency, response_text):
    """Logs AI benchmark performance into sovereign_ledger.json."""
    os.makedirs(os.path.join(BASE_DIR, "04_Legal_and_IP"), exist_ok=True)
    ledger_data = []
    
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r") as f:
                ledger_data = json.load(f)
        except Exception:
            ledger_data = []
            
    payload = {
        "event": "LOCAL_AI_BENCHMARK",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "ONLINE" if success else "OFFLINE",
        "latency_seconds": latency,
        "model_output": response_text
    }
    
    ledger_data.append(payload)
    
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger_data, f, indent=2)

if __name__ == "__main__":
    print("=== GARZA GLOBAL GRAVITON: LOCAL AI BENCHMARK ENGINE ===")
    print("Testing connection to LM Studio (http://localhost:1234/v1)...")
    
    success, latency, output = run_benchmark()
    log_benchmark_event(success, latency, output)
    
    if success:
        print(f"\n[STATUS]     LOCAL AI ENDPOINT ONLINE")
        print(f"[LATENCY]    {latency} seconds")
        print(f"[RESPONSE]   {output}")
    else:
        print(f"\n[STATUS]     LM STUDIO NOT DETECTED")
        print(f"[DETAILS]    {output}")
        print("Note: Start LM Studio local server on port 1234 to benchmark inference speed.")
        
    print("\n--- AI Benchmark Complete ---")