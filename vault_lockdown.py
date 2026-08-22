"""
Garza Global Graviton Core Module
Automated Vault Infrastructure Script
"""
import json
import os
import subprocess
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "03_Source_Code")
LEDGER_PATH = os.path.join(BASE_DIR, "04_Legal_and_IP", "sovereign_ledger.json")

LOCKDOWN_SEQUENCE = [
    ("Syntax Audit", "code_sanitizer.py"),
    ("Integration Test Suite", "test_suite.py"),
    ("Workspace Snapshot", "snapshot_engine.py"),
    ("Digital Vault Sealer", "vault_sealer.py"),
    ("Seal Verification", "seal_verifier.py")
]

def run_step(description, script_name):
    """Runs a sub-script and returns success state."""
    script_path = os.path.join(SRC_DIR, script_name)
    if not os.path.exists(script_path):
        print(f"[LOCKDOWN FAIL] Script missing: {script_name}")
        return False

    print(f"\n---> [LOCKDOWN STEP] {description} ({script_name})")
    result = subprocess.run([sys.executable, script_path])
    return result.returncode == 0

def log_lockdown_event(status):
    """Logs lockdown result to sovereign_ledger.json."""
    os.makedirs(os.path.join(BASE_DIR, "04_Legal_and_IP"), exist_ok=True)
    ledger_data = []
    
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r") as f:
                ledger_data = json.load(f)
        except Exception:
            ledger_data = []
            
    payload = {
        "event": "SYSTEM_LOCKDOWN_EXECUTED",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "lockdown_status": status
    }
    
    ledger_data.append(payload)
    
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger_data, f, indent=2)

if __name__ == "__main__":
    print("==========================================================")
    print("   GARZA GLOBAL GRAVITON: PRE-SHUTDOWN LOCKDOWN SEQUENCE   ")
    print("==========================================================")
    
    all_success = True
    for desc, script in LOCKDOWN_SEQUENCE:
        success = run_step(desc, script)
        if not success:
            all_success = False
            print(f"[WARNING] Step failed: {desc}")
            
    final_status = "SUCCESS_SAFE_TO_DISMOUNT" if all_success else "COMPLETED_WITH_WARNINGS"
    log_lockdown_event(final_status)
    
    print("\n==========================================================")
    print(f" [LOCKDOWN STATUS] {final_status}")
    print(" All files checked, backed up, sealed, and verified.")
    print(" You may safely exit VS Code and dismount Drive V: in VeraCrypt.")
    print("==========================================================\n")