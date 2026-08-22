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

REQUIRED_MODULES = [
    "identity_generator.py", "storage_engine.py", "main_pipeline.py",
    "data_indexer.py", "ledger_search.py", "snapshot_engine.py",
    "task_router.py", "health_checker.py", "vault_dashboard.py",
    "test_suite.py"
]

def run_tests():
    """Runs integration checks on vault infrastructure."""
    results = {}
    
    # Test 1: Check Source Modules
    src_dir = os.path.join(BASE_DIR, "03_Source_Code")
    missing_src = [m for m in REQUIRED_MODULES if not os.path.exists(os.path.join(src_dir, m))]
    results["Source Code Integrity"] = "PASS" if not missing_src else f"FAIL (Missing: {missing_src})"
    
    # Test 2: Check PRDs
    prd_dir = os.path.join(BASE_DIR, "02_PRDs")
    prds_present = len([f for f in os.listdir(prd_dir) if f.startswith("PRD_")]) if os.path.exists(prd_dir) else 0
    results["PRD Documentation Suite"] = "PASS" if prds_present >= 10 else f"FAIL ({prds_present}/10 found)"
    
    # Test 3: Ledger Readability
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r") as f:
                json.load(f)
            results["Sovereign Ledger State"] = "PASS"
        except Exception as e:
            results["Sovereign Ledger State"] = f"FAIL ({e})"
    else:
        results["Sovereign Ledger State"] = "FAIL (File Missing)"

    # Test 4: Disk Capacity
    _, _, free = shutil.disk_usage(BASE_DIR)
    free_mb = free / (1024 * 1024)
    results["Drive Capacity Check"] = "PASS" if free_mb > 100 else "FAIL (Low Disk Space)"

    return results

def log_test_results(results):
    """Appends test run results to sovereign_ledger.json."""
    os.makedirs(os.path.join(BASE_DIR, "04_Legal_and_IP"), exist_ok=True)
    ledger_data = []
    
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r") as f:
                ledger_data = json.load(f)
        except Exception:
            ledger_data = []
            
    all_passed = all("PASS" in str(val) for val in results.values())
    
    payload = {
        "event": "INTEGRATION_TEST_SUITE_RUN",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "overall_status": "ALL_PASS" if all_passed else "FAILURES_DETECTED",
        "test_details": results
    }
    
    ledger_data.append(payload)
    
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger_data, f, indent=2)

if __name__ == "__main__":
    print("=== GARZA GLOBAL GRAVITON: INTEGRATION TEST SUITE ===")
    
    test_results = run_tests()
    print("\n--- TEST RESULTS ---")
    for test_name, status in test_results.items():
        print(f"  [{status}] {test_name}")
        
    log_test_results(test_results)
    print("\n[SUCCESS] Test results recorded to sovereign_ledger.json")
    print("--- Test Suite Execution Complete ---")
