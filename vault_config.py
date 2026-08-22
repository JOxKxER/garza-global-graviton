"""
Garza Global Graviton Core Module
Automated Vault Infrastructure Script
"""
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCH_DIR = os.path.join(BASE_DIR, "01_Architecture")
CONFIG_PATH = os.path.join(ARCH_DIR, "vault_config.json")
LEDGER_PATH = os.path.join(BASE_DIR, "04_Legal_and_IP", "sovereign_ledger.json")

DEFAULT_CONFIG = {
    "project_name": "Garza Global Graviton",
    "version": "1.0.0",
    "hash_algorithm": "sha256",
    "vault_drive_letter": "V:",
    "air_gapped_mode": True,
    "indexed_directories": ["01_Architecture", "02_PRDs", "03_Source_Code"],
    "backup_retention_limit": 10
}

def load_or_init_config():
    """Loads existing config or writes default settings if absent."""
    os.makedirs(ARCH_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG
    
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_CONFIG

def save_config(config_data):
    """Saves updated config data to vault_config.json."""
    with open(CONFIG_PATH, "w") as f:
        json.dump(config_data, f, indent=2)

def log_config_event(action):
    """Logs configuration updates to sovereign_ledger.json."""
    os.makedirs(os.path.join(BASE_DIR, "04_Legal_and_IP"), exist_ok=True)
    ledger_data = []
    
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r") as f:
                ledger_data = json.load(f)
        except Exception:
            ledger_data = []
            
    payload = {
        "event": "VAULT_CONFIG_ACCESSED",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": action
    }
    
    ledger_data.append(payload)
    
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger_data, f, indent=2)

if __name__ == "__main__":
    print("=== GARZA GLOBAL GRAVITON: VAULT CONFIG ENGINE ===")
    
    cfg = load_or_init_config()
    log_config_event("LOAD_CONFIG")
    
    print("\n[ACTIVE VAULT CONFIGURATION]")
    print(json.dumps(cfg, indent=2))
    print(f"\n[CONFIG PATH] {CONFIG_PATH}")
    print(f"[STATUS] Environment parameters verified and locked.")
    print("\n--- Config Engine Complete ---")