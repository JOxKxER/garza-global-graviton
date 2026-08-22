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

HEADER_TEMPLATE = '"""\nGarza Global Graviton Core Module\nAutomated Vault Infrastructure Script\n"""\n'

def refactor_script(script_name):
    """Applies structural header and standard formatting checks to a target script."""
    script_path = os.path.join(SRC_DIR, script_name)
    if not os.path.exists(script_path):
        return False, f"File not found: {script_name}"

    try:
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Syntax pre-check
        ast.parse(content, filename=script_name)

        modified = False
        new_content = content

        # Ensure module docstring header exists
        if not new_content.startswith('"""') and not new_content.startswith("'''"):
            new_content = HEADER_TEMPLATE + new_content
            modified = True

        # Ensure syntax remains valid after transformation
        ast.parse(new_content, filename=script_name)

        if modified:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return True, "HEADER_ADDED_AND_SAVED"
        else:
            return True, "ALREADY_STANDARDIZED"

    except SyntaxError as e:
        return False, f"SYNTAX_ERROR: Line {e.lineno}"
    except Exception as e:
        return False, f"ERROR: {str(e)}"

def run_refactor_sweep():
    """Scans and refactors all source python files."""
    if not os.path.exists(SRC_DIR):
        return {}

    results = {}
    for f in os.listdir(SRC_DIR):
        if f.endswith(".py"):
            success, msg = refactor_script(f)
            results[f] = msg

    return results

def log_refactor_event(results):
    """Appends refactor event to sovereign_ledger.json."""
    os.makedirs(os.path.join(BASE_DIR, "04_Legal_and_IP"), exist_ok=True)
    ledger_data = []

    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r") as f:
                ledger_data = json.load(f)
        except Exception:
            ledger_data = []

    payload = {
        "event": "CODE_REFACTOR_SWEEP",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total_modules_processed": len(results),
        "refactor_summary": results
    }

    ledger_data.append(payload)

    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger_data, f, indent=2)

if __name__ == "__main__":
    print("=== GARZA GLOBAL GRAVITON: CODE REFACTOR ENGINE ===")

    sweep_results = run_refactor_sweep()

    print("\n--- REFACTOR SWEEP RESULTS ---")
    for script, status in sweep_results.items():
        print(f"  [{status.ljust(22)}] {script}")

    log_refactor_event(sweep_results)
    print("\n[SUCCESS] Refactor audit logged to sovereign_ledger.json")
    print("--- Code Refactoring Complete ---")