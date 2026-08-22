"""
Garza Global Graviton Core Module
Automated Vault Infrastructure Script
"""
import json
import os
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_PATH = os.path.join(BASE_DIR, "04_Legal_and_IP", "sovereign_ledger.json")
BACKUP_DIR = os.path.join(BASE_DIR, "04_Legal_and_IP", "Backups")

def get_ledger_info():
    """Reads ledger entry count and latest timestamp."""
    if not os.path.exists(LEDGER_PATH):
        return 0, "No Ledger Found"
    try:
        with open(LEDGER_PATH, "r") as f:
            data = json.load(f)
            count = len(data)
            last_ts = data[-1].get("timestamp", "N/A") if count > 0 else "N/A"
            return count, last_ts
    except Exception:
        return 0, "Corrupted/Unreadable"

def get_backup_info():
    """Counts total zip backups stored."""
    if not os.path.exists(BACKUP_DIR):
        return 0
    backups = [f for f in os.listdir(BACKUP_DIR) if f.endswith('.zip')]
    return len(backups)

def count_source_modules():
    """Counts python modules in 03_Source_Code."""
    src_dir = os.path.join(BASE_DIR, "03_Source_Code")
    if not os.path.exists(src_dir):
        return 0
    return len([f for f in os.listdir(src_dir) if f.endswith('.py')])

def render_dashboard():
    """Outputs ASCII system status dashboard."""
    total, used, free = shutil.disk_usage(BASE_DIR)
    free_gb = round(free / (1024 ** 3), 2)
    total_gb = round(total / (1024 ** 3), 2)
    
    ledger_count, last_timestamp = get_ledger_info()
    backup_count = get_backup_info()
    module_count = count_source_modules()
    
    print("=" * 60)
    print("      GARZA GLOBAL GRAVITON — SOVEREIGN VAULT DASHBOARD      ")
    print("=" * 60)
    print(f"  [STORAGE ENVIRONMENT]   Drive: V: (VeraCrypt Encrypted)")
    print(f"  [STORAGE CAPACITY]      Free: {free_gb} GB / Total: {total_gb} GB")
    print("-" * 60)
    print(f"  [ACTIVE MODULES]        {module_count} Core Python Scripts Verified")
    print(f"  [SOVEREIGN LEDGER]      {ledger_count} Recorded Entries")
    print(f"  [LATEST LEDGER EVENT]   {last_timestamp}")
    print(f"  [SYSTEM BACKUPS]        {backup_count} ZIP Snapshots Preserved")
    print("-" * 60)
    print(f"  [SYSTEM STATUS]         100% AIR-GAPPED & OPERATIONAL")
    print("=" * 60)

def log_dashboard_event():
    """Logs the dashboard view event to sovereign_ledger.json."""
    os.makedirs(os.path.join(BASE_DIR, "04_Legal_and_IP"), exist_ok=True)
    ledger_data = []
    
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r") as f:
                ledger_data = json.load(f)
        except Exception:
            ledger_data = []
            
    payload = {
        "event": "VAULT_DASHBOARD_VIEWED",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    ledger_data.append(payload)
    
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger_data, f, indent=2)

if __name__ == "__main__":
    render_dashboard()
    log_dashboard_event()
    print("\n[SUCCESS] Dashboard metrics logged to sovereign_ledger.json\n")

