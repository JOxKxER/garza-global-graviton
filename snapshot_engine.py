"""
Garza Global Graviton Core Module
Automated Vault Infrastructure Script
"""
import json
import os
import zipfile
from datetime import datetime

# Resolve relative paths to the vault root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIR = os.path.join(BASE_DIR, "04_Legal_and_IP", "Backups")
LEDGER_PATH = os.path.join(BASE_DIR, "04_Legal_and_IP", "sovereign_ledger.json")

def create_vault_snapshot():
    """Compresses project folders into a timestamped zip archive."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"GGG_Vault_Backup_{timestamp}.zip"
    archive_path = os.path.join(BACKUP_DIR, archive_name)
    
    folders_to_backup = ["01_Architecture", "02_PRDs", "03_Source_Code", "04_Legal_and_IP"]
    total_files = 0

    print(f"[SNAPSHOT] Creating archive: {archive_name}...")

    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for folder_name in folders_to_backup:
            folder_full_path = os.path.join(BASE_DIR, folder_name)
            
            if os.path.exists(folder_full_path):
                for root, _, files in os.walk(folder_full_path):
                    # Exclude the Backups directory to prevent infinite loops
                    if "Backups" in root:
                        continue
                        
                    for file in files:
                        full_file_path = os.path.join(root, file)
                        # Write file with relative path inside the zip
                        arcname = os.path.relpath(full_file_path, BASE_DIR)
                        zipf.write(full_file_path, arcname)
                        total_files += 1

    archive_size = os.path.getsize(archive_path)
    
    payload = {
        "event": "VAULT_SNAPSHOT_CREATED",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "archive_name": archive_name,
        "total_files_archived": total_files,
        "archive_size_bytes": archive_size
    }
    
    return archive_path, payload

def log_snapshot_event(payload):
    """Logs the snapshot event into sovereign_ledger.json."""
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
    print("=== GARZA GLOBAL GRAVITON: VAULT SNAPSHOT ENGINE ===")
    
    archive_path, log_payload = create_vault_snapshot()
    log_snapshot_event(log_payload)
    
    print(f"\n[SUCCESS] Vault snapshot created successfully!")
    print(f"[PATH] {archive_path}")
    print(f"[STATS] {log_payload['total_files_archived']} files packaged ({log_payload['archive_size_bytes']} bytes)")
    print(f"[STATUS] Event logged to sovereign_ledger.json")
    print("\n--- Snapshot Complete ---")

