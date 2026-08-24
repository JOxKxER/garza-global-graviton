"""
update_bans_schema.py - Schema Update for Blacklists & Forensic Ban Dossiers
Run with: python update_bans_schema.py
"""

import sqlite3

DB_FILE = "vault.db"

def apply_schema():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS banned_players (
            ban_id TEXT PRIMARY KEY,
            gamer_tag TEXT NOT NULL,
            steam_id TEXT,
            hardware_fingerprint TEXT,
            violation_type TEXT NOT NULL,
            confidence_score TEXT NOT NULL,
            merkle_tick_index INTEGER,
            evidence_hash TEXT NOT NULL,
            banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            banned_by TEXT DEFAULT 'Sentinel Heuristic Engine'
        );
        """)
        conn.commit()
        print("✅ Banned Players & Forensic Blacklist table initialized in vault.db!")

if __name__ == "__main__":
    apply_schema()