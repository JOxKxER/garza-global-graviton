"""
Garza Global Graviton Core Module
Automated Vault Infrastructure Script
"""
import hashlib
import json
import os
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRD_DIR = os.path.join(BASE_DIR, "02_PRDs")
LEDGER_PATH = os.path.join(BASE_DIR, "04_Legal_and_IP", "sovereign_ledger.json")

def get_next_prd_number():
    """Scans 02_PRDs to calculate the next sequential PRD number."""
    if not os.path.exists(PRD_DIR):
        os.makedirs(PRD_DIR, exist_ok=True)
        return 1
        
    files = os.listdir(PRD_DIR)
    numbers = []
    for f in files:
        match = re.match(r"PRD_(\d+)_", f)
        if match:
            numbers.append(int(match.group(1)))
            
    return max(numbers) + 1 if numbers else 1

def hash_content_sha256(content):
    """Calculates SHA-256 fingerprint of text content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def create_prd(title, context, process, rules):
    """Synthesizes structured PRD markdown file."""
    prd_num = get_next_prd_number()
    num_str = f"{prd_num:02d}"
    clean_title = re.sub(r'[^a-zA-Z0-9_]', '_', title.replace(" ", "_"))
    file_name = f"PRD_{num_str}_{clean_title}.md"
    file_path = os.path.join(PRD_DIR, file_name)

    markdown_content = f"""# Module {num_str}: {title}

## 1. Context & Goal
{context}

## 2. Process Flow
{process}

## 3. Strict Rules
{rules}
"""

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    content_hash = hash_content_sha256(markdown_content)
    return file_name, file_path, content_hash, num_str

def log_prd_event(file_name, file_hash, num_str):
    """Logs PRD creation to sovereign_ledger.json."""
    os.makedirs(os.path.join(BASE_DIR, "04_Legal_and_IP"), exist_ok=True)
    ledger_data = []
    
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r") as f:
                ledger_data = json.load(f)
        except Exception:
            ledger_data = []
            
    payload = {
        "event": "PRD_SYNTHESIZED",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "prd_module": num_str,
        "file_name": file_name,
        "sha256": file_hash
    }
    
    ledger_data.append(payload)
    
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger_data, f, indent=2)

if __name__ == "__main__":
    print("=== GARZA GLOBAL GRAVITON: PRD SYNTHESIZER ENGINE ===")
    
    next_num = get_next_prd_number()
    print(f"\n[NEXT MODULE NUMBER] {next_num:02d}")
    
    title_in = input("Enter Module Title: ").strip()
    if not title_in:
        title_in = "Automated System Worker"
        
    context_in = input("Enter Context & Goal: ").strip()
    if not context_in:
        context_in = "Auto-generated specification for workspace automation."
        
    process_in = input("Enter Key Process Steps: ").strip()
    if not process_in:
        process_in = "1. Execute input parameters.\n2. Process data locally.\n3. Output result to vault ledger."
        
    rules_in = input("Enter Strict Rules: ").strip()
    if not rules_in:
        rules_in = "- Run 100% offline.\n- Maintain relative path resolution."

    fname, fpath, fhash, mod_num = create_prd(title_in, context_in, process_in, rules_in)
    log_prd_event(fname, fhash, mod_num)
    
    print(f"\n[SUCCESS] Generated: 02_PRDs/{fname}")
    print(f"[SHA-256 HASH] {fhash}")
    print(f"[LEDGER] Synthesized PRD recorded in sovereign_ledger.json")
    print("--- PRD Synthesis Complete ---")