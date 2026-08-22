import sqlite3
import time
import shutil
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "output" / "consensus_ledger.db"
BACKUP_DIR = Path(__file__).resolve().parent.parent / "output" / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def checkpoint_and_vacuum():
    """Forces SQLite WAL log to flush into main database file and frees up unindexed pages."""
    if not DB_PATH.exists():
        return
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
        cursor = conn.cursor()
        # Truncate WAL journal into main db file
        cursor.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        conn.commit()
        conn.close()
        print(f"[MAINTENANCE] WAL Checkpoint committed successfully.")
    except Exception as e:
        print(f"[!] Maintenance error: {e}")

def create_ledger_backup():
    """Creates a consistent snapshot of the ledger database."""
    if not DB_PATH.exists():
        return
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"ledger_backup_{timestamp}.db"
    try:
        src = sqlite3.connect(str(DB_PATH))
        dst = sqlite3.connect(str(backup_file))
        with dst:
            src.backup(dst, pages=100)
        dst.close()
        src.close()
        print(f"[BACKUP] Snapshot saved to {backup_file.name}")
    except Exception as e:
        print(f"[!] Backup failed: {e}")

if __name__ == "__main__":
    checkpoint_and_vacuum()
    create_ledger_backup()
