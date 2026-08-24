"""
backup_vault.py - Automated Database & Configuration Backup Utility
Creates a secure timestamped copy of your SQLite database vault and integration files.
"""

import shutil
import os
from datetime import datetime

def backup_vault():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = "vault_backups"
    
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        
    db_file = "vault_storage.db"
    if os.path.exists(db_file):
        backup_name = os.path.join(backup_dir, f"vault_backup_{timestamp}.db")
        shutil.copy(db_file, backup_name)
        print(f"✅ Secure vault backup successfully created: {backup_name}")
    else:
        print("⚠️ Warning: vault_storage.db not found in current directory.")

if __name__ == "__main__":
    backup_vault()