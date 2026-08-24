"""
backup_manager.py - Secure Database Backup & Snapshot Engine
Compresses and archives vault storage records.
"""

import shutil
import os
import hashlib
from datetime import datetime

DB_FILE = "vault_storage.db"
BACKUP_DIR = "audit_snapshots"

def create_secure_backup():
    if not os.path.exists(DB_FILE):
        print("⚠️ No database found to back up.")
        return None

    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"vault_backup_{timestamp}.db")

    # Copy database file safely
    shutil.copyfile(DB_FILE, backup_path)

    # Compute SHA-256 integrity hash for the snapshot
    sha256_hash = hashlib.sha256()
    with open(backup_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    digest = sha256_hash.hexdigest()

    meta_path = f"{backup_path}.sha256"
    with open(meta_path, "w") as f:
        f.write(f"Snapshot: vault_backup_{timestamp}.db\nSHA256: {digest}\nTimestamp: {datetime.utcnow().isoformat()}")

    print(f"✅ Secure backup created: {backup_path} [Hash: {digest[:12]}...]")
    return backup_path

if __name__ == "__main__":
    create_secure_backup()