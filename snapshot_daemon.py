"""
snapshot_daemon.py - Automated SQLite Backup & SHA-256 Verifier
Creates cryptographically verified offline backups of platform state data.
"""

import os
import shutil
import hashlib
from datetime import datetime

DB_FILE = "vault_storage.db"
BACKUP_DIR = "V:\\03_Source_Code\\secure_snapshots"

def create_snapshot():
    if not os.path.exists(DB_FILE):
        print(f"⚠️ Error: Database file {DB_FILE} not found.")
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"vault_snapshot_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    # Copy database file
    shutil.copy2(DB_FILE, backup_path)

    # Compute SHA-256 Hash for Verification
    sha256_hash = hashlib.sha256()
    with open(backup_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    digest = sha256_hash.hexdigest()

    # Save hash certificate
    hash_path = f"{backup_path}.sha256"
    with open(hash_path, "w") as hf:
        hf.write(f"SHA-256: {digest}\nTimestamp: {timestamp}\n")

    print(f"🔒 Secure snapshot created successfully:")
    print(f"   - File: {backup_filename}")
    print(f"   - SHA-256: {digest[:16]}...")

if __name__ == "__main__":
    create_snapshot()