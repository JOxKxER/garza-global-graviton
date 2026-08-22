"""
Garza Global Graviton Core Module
Automated Vault Infrastructure Script
"""
import ast
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "03_Source_Code")
LEDGER_PATH = os.path.join(BASE_DIR, "04_Legal_and_IP", "sovereign_ledger.json")

def audit_python_scripts():
    """Scans and parses all python scripts in 03_Source_Code for syntax validity."""
    if not os.path.exists(SRC_DIR):
        print(f"[ERROR] Source code directory not found at: {SRC_DIR}")
        return {}

    audit_results = {}
    py_files = [f for f in os.listdir(SRC_DIR) if f.endswith('.py')]

    for file_name in py_files:
        full_path = os.path.join(SRC_DIR, file_name)
        
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Perform native Abstract Syntax Tree parsing check
            ast.parse(content, filename=file_name)
            
            line_count = len(content.splitlines())
            audit_results[file_name] = {
                "status": "PASS",
                "lines": line_count,
                "size_bytes": os.path.getsize(full_path)
            }
        except SyntaxError as e:
            audit_results[file_name] = {
                "status": f"SYNTAX_ERROR (Line {e.lineno})",
                "details": str(e)
            }
        except Exception as e:
            audit_results[file_name] = {
                "status": f"READ_ERROR ({str(e)})"
            }

    return audit_results

def log_audit_event(results):
    """Appends code quality audit metrics to sovereign_ledger.json."""
    os.makedirs(os.path.join(BASE_DIR, "04_Legal_and_IP"), exist_ok=True)
    ledger_data = []
    
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r") as f:
                ledger_data = json.load(f)
        except Exception:
            ledger_data = []
            
    total_files = len(results)
    passed_files = sum(1 for v in results.values() if v.get("status") == "PASS")
    
    payload = {
        "event": "CODE_SYNTAX_AUDIT",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total_modules_scanned": total_files,
        "modules_passed": passed_files,
        "all_passed": (passed_files == total_files),
        "audit_details": results
    }
    
    ledger_data.append(payload)
    
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger_data, f, indent=2)

if __name__ == "__main__":
    print("=== GARZA GLOBAL GRAVITON: CODE SANITIZER & SYNTAX AUDITOR ===")
    
    results = audit_python_scripts()
    
    print("\n--- SYNTAX & AUDIT RESULTS ---")
    for script_name, data in results.items():
        status = data.get("status")
        lines = data.get("lines", "N/A")
        print(f"  [{status}] {script_name.ljust(25)} ({lines} lines)")
        
    log_audit_event(results)
    print(f"\n[SUCCESS] Scanned {len(results)} source modules. Audit logged to sovereign_ledger.json")
    print("--- Code Sanitization Complete ---")