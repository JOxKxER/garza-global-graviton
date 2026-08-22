"""
Garza Global Graviton Core Module
Automated Vault Infrastructure Script
"""
import hashlib
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGAL_DIR = os.path.join(BASE_DIR, "04_Legal_and_IP")
BACKUP_DIR = os.path.join(LEGAL_DIR, "Backups")
LEDGER_PATH = os.path.join(LEGAL_DIR, "sovereign_ledger.json")
MANIFEST_PATH = os.path.join(LEGAL_DIR, "SEAL_MANIFEST.json")

def hash_file_sha256(file_path):
    """Calculates live SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def verify_vault_seal():
    """Validates live backup file against the recorded seal manifest."""
    if not os.path.exists(MANIFEST_PATH):
        print("[ERROR] Seal manifest not found! Run vault_sealer.py first.")
        return False, "MANIFEST_MISSING"

    try:
        with open(MANIFEST_PATH, "r") as f:
            manifest = json.load(f)
    except Exception as e:
        print(f"[ERROR] Could not read seal manifest: {e}")
        return False, "MANIFEST_CORRUPTED"

    target_name = manifest.get("target_archive")
    expected_hash = manifest.get("archive_sha256")
    target_path = os.path.join(BACKUP_DIR, target_name)

    if not os.path.exists(target_path):
        print(f"[ERROR] Sealed backup file missing: {target_name}")
        return False, "ARCHIVE_MISSING"

    live_hash = hash_file_sha256(target_path)
    
    is_valid = (live_hash == expected_hash)
    status_str = "SEAL_VALID" if is_valid else "SEAL_TAMPERED"

    print(f"\n[TARGET BACKUP]  {target_name}")
    print(f"[EXPECTED HASH]  {expected_hash}")
    print(f"[LIVE HASH]      {live_hash}")
    
    return is_valid, status_str

def log_verification_event(status_str):
    """Logs verification result into sovereign_ledger.json."""
    ledger_data = []
    
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r") as f:
                ledger_data = json.load(f)
        except Exception:
            ledger_data = []
            
    payload = {
        "event": "VAULT_SEAL_VERIFICATION",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "result": status_str
    }
    
    ledger_data.append(payload)
    
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger_data, f, indent=2)

if __name__ == "__main__":
    print("=== GARZA GLOBAL GRAVITON: VAULT SEAL VERIFIER ===")
    
    valid, status = verify_vault_seal()
    log_verification_event(status)
    
    if valid:
        print("\n[SUCCESS] Cryptographic Seal Intact. No archive tampering detected.")
    else:
        print(f"\n[CRITICAL ALERT] Vault seal check failed! Status: {status}")
        
    print("--- Seal Verification Complete ---")