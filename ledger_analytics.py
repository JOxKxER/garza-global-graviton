"""
Garza Global Graviton Core Module
Automated Vault Infrastructure Script
"""
from collections import Counter
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_PATH = os.path.join(BASE_DIR, "04_Legal_and_IP", "sovereign_ledger.json")

def analyze_ledger():
    """Parses ledger records and computes summary analytics."""
    if not os.path.exists(LEDGER_PATH):
        print(f"[ERROR] Ledger file not found at: {LEDGER_PATH}")
        return None

    try:
        with open(LEDGER_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read ledger: {e}")
        return None

    if not isinstance(data, list) or len(data) == 0:
        print("[NOTICE] Ledger is empty or invalid format.")
        return None

    total_records = len(data)
    event_counts = Counter(entry.get("event", "UNKNOWN_EVENT") for entry in data)
    
    timestamps = [entry.get("timestamp") for entry in data if "timestamp" in entry]
    first_event = timestamps[0] if timestamps else "N/A"
    last_event = timestamps[-1] if timestamps else "N/A"

    return {
        "total_records": total_records,
        "event_counts": dict(event_counts),
        "first_event": first_event,
        "last_event": last_event
    }

def log_analytics_event(summary):
    """Appends the analytics execution event to sovereign_ledger.json."""
    ledger_data = []
    
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r") as f:
                ledger_data = json.load(f)
        except Exception:
            ledger_data = []
            
    payload = {
        "event": "LEDGER_ANALYTICS_EXECUTED",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total_ledger_entries_analyzed": summary["total_records"] if summary else 0
    }
    
    ledger_data.append(payload)
    
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger_data, f, indent=2)

if __name__ == "__main__":
    print("=== GARZA GLOBAL GRAVITON: LEDGER ANALYTICS ENGINE ===")
    
    metrics = analyze_ledger()
    
    if metrics:
        print(f"\n[TOTAL ENTRIES]    {metrics['total_records']} Recorded Events")
        print(f"[FIRST EVENT]      {metrics['first_event']}")
        print(f"[LAST EVENT]       {metrics['last_event']}")
        print("\n--- EVENT DISTRIBUTION ---")
        for event_name, count in metrics['event_counts'].items():
            print(f"  - {event_name.ljust(32)}: {count}")
            
        log_analytics_event(metrics)
        print(f"\n[SUCCESS] Analytics sweep complete and logged to sovereign_ledger.json")
    else:
        print("[WARNING] No metrics generated.")
        
    print("--- Analytics Complete ---")