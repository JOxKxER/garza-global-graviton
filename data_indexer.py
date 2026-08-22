"""
Garza Global Graviton Core Module
Automated Vault Infrastructure Script
"""
import hashlib
import json
import os
from datetime import datetime

# Get the absolute path of the root directory (one level up from 03_Source_Code)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGAL_DIR = os.path.join(BASE_DIR, "04_Legal_and_IP")
LEDGER_PATH = os.path.join(LEGAL_DIR, "sovereign_ledger.json")

def hash_file(file_path):
    """Calculates SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        return f"Error: {str(e)}"

def run_vault_indexer(target_dirs):
    """Scans target directories and generates an index payload."""
    indexed_files = []
    
    for folder_name in target_dirs:
        folder_path = os.path.join(BASE_DIR, folder_name)
        if os.path.exists(folder_path):
            for root, _, files in os.walk(folder_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    file_hash = hash_file(full_path)
                    file_size = os.path.getsize(full_path)
                    
                    # Store relative path for cleaner display
                    rel_path = os.path.relpath(full_path, BASE_DIR)
                    
                    indexed_files.append({
                        "file_path": rel_path,
                        "size_bytes": file_size,
                        "sha256_hash": file_hash
                    })
                    
    payload = {
        "event": "VAULT_INDEX_RUN",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total_files_indexed": len(indexed_files),
        "files": indexed_files
    }
    return payload

def save_to_ledger(payload):
    """Appends index record to sovereign_ledger.json in 04_Legal_and_IP."""
    os.makedirs(LEGAL_DIR, exist_ok=True)
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
        
    print(f"\n[SUCCESS] Vault index recorded in: {LEDGER_PATH}")
    print(f"[STATUS] Total indexed records in ledger: {len(ledger_data)}")

if __name__ == "__main__":
    print("=== GARZA GLOBAL GRAVITON: VAULT DATA INDEXER ===")
    
    # Folders to index
    folders_to_scan = ["01_Architecture", "02_PRDs", "03_Source_Code"]
    
    # 1. Run indexer
    index_payload = run_vault_indexer(folders_to_scan)
    
    print(f"\nIndexed {index_payload['total_files_indexed']} files across project directories.")
    
    # 2. Save payload
    save_to_ledger(index_payload)
    
    print("\n--- Vault Indexing Complete ---")
