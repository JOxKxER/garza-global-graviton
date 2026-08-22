"""
Garza Global Graviton Core Module
Automated Vault Infrastructure Script
"""
import json
import os

# Resolve path relative to the root vault folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_PATH = os.path.join(BASE_DIR, "04_Legal_and_IP", "sovereign_ledger.json")

def load_ledger():
    """Loads and validates the sovereign ledger file."""
    if not os.path.exists(LEDGER_PATH):
        print(f"[ERROR] Ledger file not found at: {LEDGER_PATH}")
        return None
    
    try:
        with open(LEDGER_PATH, "r") as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"[ERROR] Sovereign ledger is corrupted or invalid JSON: {e}")
        return None

def search_ledger(ledger, query):
    """Searches through all ledger entries for a matching string."""
    query_str = str(query).lower()
    matches = []

    for index, entry in enumerate(ledger):
        entry_str = json.dumps(entry).lower()
        if query_str in entry_str:
            matches.append((index, entry))
            
    return matches

if __name__ == "__main__":
    print("=== GARZA GLOBAL GRAVITON: LEDGER SEARCH & AUDIT ===")
    
    # 1. Load and verify ledger
    ledger = load_ledger()
    
    if ledger is not None:
        print(f"[AUDIT] Ledger successfully loaded and verified.")
        print(f"[AUDIT] Total records logged: {len(ledger)}\n")
        
        # 2. Interactive Search
        search_term = input("Enter search keyword (e.g., 'identity_key', 'PRD', 'VAULT_INDEX'): ").strip()
        
        if search_term:
            results = search_ledger(ledger, search_term)
            print(f"\nFound {len(results)} matching record(s) for '{search_term}':\n")
            
            for record_idx, record_data in results:
                print(f"--- Record #{record_idx + 1} ---")
                print(json.dumps(record_data, indent=2))
                print("-" * 30)
        else:
            print("No search term entered. Audit complete.")
            
    print("\n--- Search & Audit Complete ---")
