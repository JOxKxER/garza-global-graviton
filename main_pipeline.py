"""
Garza Global Graviton Core Module
Automated Vault Infrastructure Script
"""
import hashlib
import json
import os
from datetime import datetime

# Path to local ledger in 04_Legal_and_IP
LEDGER_PATH = os.path.join("04_Legal_and_IP", "sovereign_ledger.json")

def generate_key(name, dob, salt):
    """Generates a 256-bit SHA-256 cryptographic hash."""
    raw_payload = f"{name}:{dob}:{salt}"
    sha256_hash = hashlib.sha256(raw_payload.encode('utf-8')).hexdigest()
    
    return {
        "status": "success",
        "identity_key": sha256_hash,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "system": "Garza Global Graviton - Sovereign Vault"
    }

def save_to_ledger(payload):
    """Appends payload to the sovereign ledger file."""
    os.makedirs("04_Legal_and_IP", exist_ok=True)
    ledger_data = []
    
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r") as f:
                ledger_data = json.load(f)
        except Exception:
            ledger_data = []
            
    ledger_data.append(payload)
    
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger_data, f, indent=2)
        
    print(f"\n[SUCCESS] Key written to {LEDGER_PATH}")
    print(f"[STATUS] Total saved entries in sovereign ledger: {len(ledger_data)}")

if __name__ == "__main__":
    print("=== GARZA GLOBAL GRAVITON: MASTER PIPELINE ===")
    
    # Get interactive inputs from user
    user_name = input("Enter Full Name: ")
    user_dob = input("Enter DOB (YYYY-MM-DD): ")
    user_salt = input("Enter Hardware Salt: ")
    
    # 1. Generate identity key
    identity_payload = generate_key(user_name, user_dob, user_salt)
    
    # 2. Save payload directly to ledger
    save_to_ledger(identity_payload)
    
    print("\n--- Pipeline Execution Complete ---")
