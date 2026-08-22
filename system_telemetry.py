import os
import sys
import json
import shutil
import datetime

# Force UTF-8 encoding for standard streams on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Folder prefixes to scan for in parent directory
REQUIRED_PREFIXES = ["01_", "02_", "03_", "04_"]

def run_telemetry_audit():
    print("=" * 65)
    print(" GARZA GLOBAL GRAVITON: AUTOMATED SYSTEM TELEMETRY AUDITOR")
    print("=" * 65)

    print("\n[STORAGE AUDIT] Inspecting workspace drive allocation...")
    total, used, free = shutil.disk_usage(".")
    
    total_gb = total / (1024 ** 3)
    used_gb = used / (1024 ** 3)
    free_gb = free / (1024 ** 3)

    print(f"  + Drive Total Space: {total_gb:.2f} GB")
    print(f"  + Drive Used Space : {used_gb:.2f} GB")
    print(f"  + Drive Free Space : {free_gb:.2f} GB")

    print("\n[DIRECTORY AUDIT] Verifying sovereign workspace paths...")
    parent_dir = ".."
    parent_contents = os.listdir(parent_dir) if os.path.exists(parent_dir) else []
    
    verified_count = 0

    for prefix in REQUIRED_PREFIXES:
        match = next((item for item in parent_contents if item.startswith(prefix) and os.path.isdir(os.path.join(parent_dir, item))), None)
        if match:
            verified_count += 1
            print(f"  + Path [../{match}] -> VERIFIED")
        else:
            print(f"  - Path [../{prefix}*] -> MISSING")

    all_paths_ok = (verified_count == len(REQUIRED_PREFIXES))

    print("\n" + "=" * 65)
    print(f" TELEMETRY SUMMARY: Drive Space {free_gb:.1f}GB Free | Paths: {verified_count}/{len(REQUIRED_PREFIXES)} Verified")
    print("=" * 65)

    # Log Telemetry to Ledger
    ledger_path = os.path.join("..", "04_Legal_and_IP", "sovereign_ledger.json")
    if not os.path.exists(ledger_path):
        # Fallback search if Legal folder has slightly different name
        for item in parent_contents:
            if item.startswith("04_") and os.path.isdir(os.path.join(parent_dir, item)):
                ledger_path = os.path.join("..", item, "sovereign_ledger.json")
                break

    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                ledger = json.load(f)
            entry = {
                "event": "SYSTEM_TELEMETRY_AUDIT_COMPLETE",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
                "free_disk_gb": round(free_gb, 2),
                "paths_verified": f"{verified_count}/{len(REQUIRED_PREFIXES)}",
                "status": "PASS" if all_paths_ok else "WARNING"
            }
            ledger.append(entry)
            with open(ledger_path, "w", encoding="utf-8") as f:
                json.dump(ledger, f, indent=2)
            print("[STATUS] System telemetry state logged to sovereign_ledger.json")
        except Exception as e:
            print(f"[WARNING] Could not update ledger: {e}")

    print("\n--- System Telemetry Audit Complete ---")

if __name__ == "__main__":
    run_telemetry_audit()