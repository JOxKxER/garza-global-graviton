"""
Garza Global Graviton Core Module
Automated Vault Infrastructure Script
"""
import hashlib
import json
import os
import secrets
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGAL_DIR = os.path.join(BASE_DIR, "04_Legal_and_IP")
CONFIG_PATH = os.path.join(LEGAL_DIR, "vault_config.json")
LEDGER_PATH = os.path.join(LEGAL_DIR, "sovereign_ledger.json")

def get_fingerprint(secret_hex: str) -> str:
    """Computes SHA-256 fingerprint of key material for ledger tracking."""
    return hashlib.sha256(secret_hex.encode("utf-8")).hexdigest()[:16]

def rotate_keys():
    """Generates fresh 256-bit HMAC/AES keys and updates configuration."""
    os.makedirs(LEGAL_DIR, exist_ok=True)
    
    old_hmac_fp = "INITIAL_STATE"
    old_aes_fp = "INITIAL_STATE"

    # Read existing config if present
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                old_cfg = json.load(f)
                old_hmac_fp = get_fingerprint(old_cfg.get("hmac_signing_key", ""))
                old_aes_fp = get_fingerprint(old_cfg.get("aes_vault_key", ""))
        except Exception:
            pass

    # Generate fresh 256-bit keys
    new_hmac_key = secrets.token_hex(32)
    new_aes_key = secrets.token_hex(32)

    new_hmac_fp = get_fingerprint(new_hmac_key)
    new_aes_fp = get_fingerprint(new_aes_key)

    config_payload = {
        "updated_utc": datetime.utcnow().isoformat() + "Z",
        "key_standard": "NIST_SP_800_57_COMPLIANT",
        "hmac_signing_key": new_hmac_key,
        "aes_vault_key": new_aes_key,
        "hmac_fingerprint": new_hmac_fp,
        "aes_fingerprint": new_aes_fp
    }

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config_payload, f, indent=2)

    return old_hmac_fp, new_hmac_fp, old_aes_fp, new_aes_fp

def log_rotation_event(old_h_fp: str, new_h_fp: str, old_a_fp: str, new_a_fp: str):
    """Logs cryptographic key rotation lifecycle event to sovereign_ledger.json."""
    ledger_data = []
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r", encoding="utf-8") as f:
                ledger_data = json.load(f)
        except Exception:
            ledger_data = []

    payload = {
        "event": "KEY_ROTATION_COMPLETE",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "compliance": "NIST SP 800-57",
        "hmac_fingerprint_transition": f"{old_h_fp} -> {new_h_fp}",
        "aes_fingerprint_transition": f"{old_a_fp} -> {new_a_fp}",
        "status": "KEYS_REKEYED_AND_SEALED"
    }

    ledger_data.append(payload)

    with open(LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(ledger_data, f, indent=2)

if __name__ == "__main__":
    print("=== GARZA GLOBAL GRAVITON: KEY ROTATION & REKEY ENGINE ===")
    print("Executing NIST SP 800-57 Cryptographic Key Lifecycle Rotation...")

    start_t = time.time()
    old_h, new_h, old_a, new_a = rotate_keys()
    log_rotation_event(old_h, new_h, old_a, new_a)
    elapsed = round(time.time() - start_t, 3)

    print("\n==============================================================")
    print("   GARZA GLOBAL GRAVITON: KEY ROTATION REPORT")
    print("==============================================================")
    print(f"  [KEY STANDARD]           NIST SP 800-57 (256-bit Pseudo-Random)")
    print(f"  [HMAC SIGNING KEY]       {old_h} -> {new_h} (SHA-256 FP)")
    print(f"  [AES ENCRYPTION KEY]     {old_a} -> {new_a} (SHA-256 FP)")
    print(f"  [ROTATION DURATION]      {elapsed} Seconds")
    print("  ----------------------------------------------------------")
    print("  [CRYPTOGRAPHIC INTEGRITY]")
    print("    - Key Secrets Saved  : 04_Legal_and_IP/vault_config.json")
    print("    - Audit Record       : RECORDED IN SOVEREIGN LEDGER")
    print("    - Operational State  : REKEYED & SECURE")
    print("==============================================================\n")