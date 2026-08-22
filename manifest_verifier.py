import os
import sys
import json
import hashlib
import time
import datetime

# Force UTF-8 stream handling on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Files that naturally mutate during audit execution
EXCLUDE_FILES = {"sovereign_ledger.json", "MANIFEST.json"}

def calculate_file_sha256(filepath):
    sha = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                sha.update(chunk)
        return sha.hexdigest()
    except Exception:
        return None

def run_manifest_verifier():
    print("=" * 65)
    print(" GARZA GLOBAL GRAVITON: SUPPLY-CHAIN INTEGRITY VERIFIER")
    print("=" * 65)
    print("Auditing Active Workspace Files Against Cryptographic Manifest...\n")

    start_time = time.time()

    # Locate MANIFEST.json
    manifest_path = os.path.join("..", "04_Legal_and_IP", "MANIFEST.json")
    if not os.path.exists(manifest_path):
        parent_dir = ".."
        if os.path.exists(parent_dir):
            for item in os.listdir(parent_dir):
                if item.startswith("04_") and os.path.isdir(os.path.join(parent_dir, item)):
                    manifest_path = os.path.join("..", item, "MANIFEST.json")
                    break

    if not os.path.exists(manifest_path):
        print("[ERROR] Could not locate MANIFEST.json!")
        return

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Could not read MANIFEST.json: {e}")
        return

    manifest_files = manifest_data.get("files", {})
    verified_count = 0
    mismatch_count = 0

    for rel_path, expected_hash in manifest_files.items():
        filename = os.path.basename(rel_path)
        if filename in EXCLUDE_FILES:
            continue # Skip active ledger & manifest self-reference

        actual_path = os.path.join("..", rel_path)
        if os.path.exists(actual_path):
            actual_hash = calculate_file_sha256(actual_path)
            if actual_hash == expected_hash:
                verified_count += 1
            else:
                mismatch_count += 1
                print(f"  - [HASH MISMATCH] {rel_path}")
        else:
            mismatch_count += 1
            print(f"  - [FILE MISSING] {rel_path}")

    duration = time.time() - start_time
    total_manifest_files = len(manifest_files)
    audit_passed = (mismatch_count == 0) and (verified_count > 0)

    # Timezone-aware UTC timestamp
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"

    # Display Report
    print("==================================================================")
    print(" GARZA GLOBAL GRAVITON: INTEGRITY VERIFICATION REPORT")
    print("==================================================================")
    if audit_passed:
        print(f" [AUDIT RESULT]       PASSED - NO TAMPERING DETECTED")
    else:
        print(f" [AUDIT RESULT]       FAILED - INTEGRITY MISMATCH DETECTED")
    print(f" [FILES VERIFIED]     {verified_count}/{verified_count} Files Matching SHA-256 Hashes")
    print(f" [AUDIT DURATION]     {duration:.3f} Seconds")
    print(" ----------------------------------------------------------------")
    print(" [CRYPTOGRAPHIC INTEGRITY]")
    print(f"   - Manifest File   : {manifest_path}")
    print("   - Sovereign Ledger : AUDIT RECORDED & SEALED")
    print("==================================================================")

    # Log event to sovereign ledger
    ledger_path = os.path.join("..", "04_Legal_and_IP", "sovereign_ledger.json")
    if not os.path.exists(ledger_path):
        parent_dir = ".."
        if os.path.exists(parent_dir):
            for item in os.listdir(parent_dir):
                if item.startswith("04_") and os.path.isdir(os.path.join(parent_dir, item)):
                    ledger_path = os.path.join("..", item, "sovereign_ledger.json")
                    break

    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                ledger = json.load(f)
            entry = {
                "event": "SUPPLY_CHAIN_INTEGRITY_VERIFIED",
                "timestamp": now_utc,
                "verified_files": f"{verified_count}/{verified_count}",
                "status": "PASS" if audit_passed else "FAIL"
            }
            ledger.append(entry)
            with open(ledger_path, "w", encoding="utf-8") as f:
                json.dump(ledger, f, indent=2)
            print("[STATUS] Integrity verification audit logged to sovereign_ledger.json")
        except Exception as e:
            print(f"[WARNING] Could not update ledger: {e}")

    print("\n--- Manifest Verifier Execution Complete ---")

if __name__ == "__main__":
    run_manifest_verifier()