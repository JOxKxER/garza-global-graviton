"""
Garza Global Graviton Core Module
Automated Vault Infrastructure Script
"""
import hashlib
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_PATH = os.path.join(BASE_DIR, "04_Legal_and_IP", "sovereign_ledger.json")

def derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derives a 256-bit key using PBKDF2-HMAC-SHA256."""
    return hashlib.pbkdf2_hmac('sha256', passphrase.encode('utf-8'), salt, 100000, dklen=32)

def xor_transform(data: bytes, key: bytes) -> bytes:
    """Applies byte-level XOR transformation with derived key."""
    key_len = len(key)
    return bytes(b ^ key[i % key_len] for i, b in enumerate(data))

def encrypt_file(file_path: str, passphrase: str) -> str:
    """Encrypts target file and saves as .enc."""
    if not os.path.exists(file_path):
        return None
        
    with open(file_path, "rb") as f:
        plaintext = f.read()
        
    salt = os.urandom(16)
    key = derive_key(passphrase, salt)
    ciphertext = xor_transform(plaintext, key)
    
    out_path = file_path + ".enc"
    with open(out_path, "wb") as f:
        f.write(salt + ciphertext)
        
    return out_path

def decrypt_file(enc_path: str, passphrase: str) -> str:
    """Decrypts a .enc file and restores original file."""
    if not os.path.exists(enc_path) or not enc_path.endswith('.enc'):
        return None
        
    with open(enc_path, "rb") as f:
        content = f.read()
        
    if len(content) < 16:
        return None
        
    salt = content[:16]
    ciphertext = content[16:]
    
    key = derive_key(passphrase, salt)
    plaintext = xor_transform(ciphertext, key)
    
    out_path = enc_path[:-4]  # Remove .enc
    with open(out_path, "wb") as f:
        f.write(plaintext)
        
    return out_path

def log_vault_event(action: str, target_file: str):
    """Logs secret vault operation to sovereign_ledger.json."""
    os.makedirs(os.path.join(BASE_DIR, "04_Legal_and_IP"), exist_ok=True)
    ledger_data = []
    
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r") as f:
                ledger_data = json.load(f)
        except Exception:
            ledger_data = []
            
    payload = {
        "event": "SECRET_VAULT_OPERATION",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": action,
        "target_file": os.path.basename(target_file)
    }
    
    ledger_data.append(payload)
    
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger_data, f, indent=2)

if __name__ == "__main__":
    print("=== GARZA GLOBAL GRAVITON: SECRET VAULT ENCRYPTOR ===")
    
    print("\n1. Encrypt a file")
    print("2. Decrypt a file (.enc)")
    mode = input("Select mode (1 or 2): ").strip()
    
    target = input("Enter full or relative file path: ").strip()
    pwd = input("Enter encryption passphrase: ").strip()
    
    if mode == "1" and target and pwd:
        res = encrypt_file(target, pwd)
        if res:
            log_vault_event("FILE_ENCRYPTED", res)
            print(f"\n[SUCCESS] Encrypted file saved to: {res}")
        else:
            print("\n[ERROR] Encryption failed. Check file path.")
    elif mode == "2" and target and pwd:
        res = decrypt_file(target, pwd)
        if res:
            log_vault_event("FILE_DECRYPTED", res)
            print(f"\n[SUCCESS] Decrypted file restored to: {res}")
        else:
            print("\n[ERROR] Decryption failed. Verify file path and passphrase.")
    else:
        print("\n[CANCELLED] Invalid selection or empty inputs.")
        
    print("--- Secret Vault Operation Complete ---")