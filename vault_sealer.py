"""
Garza Global Graviton Core Module
Automated Vault Infrastructure Script
"""
import hashlib
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIR = os.path.join(BASE_DIR, "04_Legal_and_IP", "Backups")
LEGAL_DIR = os.path.join(BASE_DIR, "04_Legal_and_IP")
LEDGER_PATH = os.path.join(LEGAL_DIR, "sovereign_ledger.json")
MANIFEST_PATH = os.path.join(LEGAL_DIR, "SEAL_MANIFEST.json")

def get_latest_backup():
    """Finds the most recently created zip file in Backups/."""
    if not os.path.exists(BACKUP_DIR):
        return None
    backups = [os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if f.endswith('.zip')]
    if not backups:
        return None
    return max(backups, key=os.path.getctime)

def hash_file_sha256(file_path):
    """Calculates SHA-256 hash of a large file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def generate_vault_seal():
    """Generates a cryptographic seal manifest for the latest backup."""
    latest_zip = get_latest_backup()
    if not latest_zip:
        print("[ERROR] No ZIP backups found in 04_Legal_and_IP/Backups/. Run snapshot_engine.py first.")
        return None, None
    
    zip_name = os.path.basename(latest_zip)
    zip_hash = hash_file_sha256(latest_zip)
    zip_size = os.path.getsize(latest_zip)
    
    seal_manifest = {
        "seal_event": "VAULT_DIGITAL_SEAL_CREATED",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "target_archive": zip_name,
        "archive_sha256": zip_hash,
        "archive_size_bytes": zip_size,
        "status": "SEAL_INTACT"
    }
    
    # Save standalone manifest
    with open(MANIFEST_PATH, "w") as f:
        json.dump(seal_manifest, f, indent=2)
        
    return latest_zip, seal_manifest

def log_seal_event(payload):
    """Logs the seal creation event to sovereign_ledger.json."""
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

if __name__ == "__main__":
    print("=== GARZA GLOBAL GRAVITON: VAULT CRYPTOGRAPHIC SEALER ===")
    
    target_zip, seal_data = generate_vault_seal()
    
    if seal_data:
        log_seal_event(seal_data)
        print(f"\n[TARGET BACKUP] {os.path.basename(target_zip)}")
        print(f"[SHA-256 HASH]  {seal_data['archive_sha256']}")
        print(f"[MANIFEST FILE] Written to {MANIFEST_PATH}")
        print(f"[SUCCESS] Digital seal verification recorded in sovereign_ledger.json")
        
    print("\n--- Vault Sealing Complete ---")