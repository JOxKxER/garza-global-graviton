import sqlite3
import requests
import json
import time

# Configure local Ollama endpoint for Qwen 2.5
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"

def query_joker(prompt):
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    response = requests.post(OLLAMA_URL, json=payload)
    if response.status_code == 200:
        return response.json().get("response", "")
    else:
        return f"Error: {response.status_code}"

def init_telemetry_db():
    conn = sqlite3.connect("joker_telemetry.db")
    cursor = conn.cursor()
    # Enable Write-Ahead Logging for high-frequency concurrency
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            timestamp REAL,
            sensor_id TEXT,
            reading REAL,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("[JOKER] Telemetry database initialized with WAL mode.")

if __name__ == "__main__":
    init_telemetry_db()
    
    # Prompt Joker to self-bootstrap its edge automation logic
    bootstrap_prompt = (
        "You are Joker, an edge automation daemon. Write a Python snippet "
        "that polls a dummy serial sensor port every 5 seconds and logs "
        "the output into the joker_telemetry.db database."
    )
    
    print("[JOKER] Generating core automation routine...")
    code_output = query_joker(bootstrap_prompt)
    print(code_output)