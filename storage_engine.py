"""
Garza Global Graviton Core Module
Automated Vault Infrastructure Script
"""
import json
import os
from datetime import datetime

# Path to local ledger in 04_Legal_and_IP
LEDGER_PATH = os.path.join("04_Legal_and_IP", "sovereign_ledger.json")

def append_to_ledger(payload):
    # Ensure destination folder exists
    os.makedirs("04_Legal_and_IP", exist_ok=True)
    
    # Initialize empty list
    ledger_data = []
    
    # Load existing records if ledger file already exists
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r") as f:
                ledger_data = json.load(f)
        except Exception:
            ledger_data = []
            
    # Append new record
    ledger_data.append(payload)
    
    # Write updated records back to ledger
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger_data, f, indent=2)
        
    print(f"\n[SUCCESS] Record appended to {LEDGER_PATH}")
    print(f"[STATUS] Total saved entries in sovereign ledger: {len(ledger_data)}")

if __name__ == "__main__":
    # Automatic test payload
    sample_payload = {
        "status": "success",
        "identity_key": "a8f9c2d1e0b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "system": "Garza Global Graviton - Sovereign Vault"
    }
    
    append_to_ledger(sample_payload)
