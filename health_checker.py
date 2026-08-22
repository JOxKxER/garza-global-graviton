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

REQUIRED_SCRIPTS = [
    "identity_generator.py", "storage_engine.py", "main_pipeline.py",
    "data_indexer.py", "ledger_search.py", "snapshot_engine.py",
    "task_router.py", "health_checker.py"
]

def check_disk_space():
    """Returns disk usage stats in MB."""
    total, used, free = shutil.disk_usage(BASE_DIR)
    return {
        "total_mb": round(total / (1024 * 1024), 2),
        "used_mb": round(used / (1024 * 1024), 2),
        "free_mb": round(free / (1024 * 1024), 2)
    }

def verify_source_files():
    """Checks for existence of all required python modules."""
    source_dir = os.path.join(BASE_DIR, "03_Source_Code")
    missing_files = []
    
    for script in REQUIRED_SCRIPTS:
        if not os.path.exists(os.path.join(source_dir, script)):
            missing_files.append(script)
            
    return missing_files

def log_health_status(disk_stats, missing_files):
    """Appends health status event to sovereign_ledger.json."""
    os.makedirs(os.path.join(BASE_DIR, "04_Legal_and_IP"), exist_ok=True)
    ledger_data = []
    
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r") as f:
                ledger_data = json.load(f)
        except Exception:
            ledger_data = []
            
    status = "HEALTHY" if not missing_files else "DEGRADED"
    
    payload = {
        "event": "SYSTEM_HEALTH_CHECK",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "system_status": status,
        "disk_space": disk_stats,
        "missing_modules": missing_files,
        "total_modules_expected": len(REQUIRED_SCRIPTS)
    }
    
    ledger_data.append(payload)
    
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger_data, f, indent=2)
        
    return payload

if __name__ == "__main__":
    print("=== GARZA GLOBAL GRAVITON: SYSTEM HEALTH CHECKER ===")
    
    disk = check_disk_space()
    missing = verify_source_files()
    
    print(f"\n[DISK SPACE] Free: {disk['free_mb']} MB / Total: {disk['total_mb']} MB")
    
    if missing:
        print(f"[WARNING] Missing modules detected: {missing}")
    else:
        print(f"[MODULES] All {len(REQUIRED_SCRIPTS)} source scripts present & verified.")
        
    health_payload = log_health_status(disk, missing)
    
    print(f"[STATUS] System state: {health_payload['system_status']}")
    print(f"[SUCCESS] Health metrics recorded to sovereign_ledger.json")
    print("\n--- Health Check Complete ---")

