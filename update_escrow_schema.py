"""
update_escrow_schema.py - Escrow & Transaction Schema Initializer
Run with: python update_escrow_schema.py
"""

import sqlite3

DB_FILE = "vault.db"

def apply_schema():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS tournament_escrows (
            escrow_id TEXT PRIMARY KEY,
            tournament_title TEXT NOT NULL,
            organizer_tag TEXT NOT NULL,
            prize_pool_tokens INTEGER NOT NULL,
            status TEXT DEFAULT 'LOCKED_IN_ESCROW', -- LOCKED_IN_ESCROW, DISBURSED, REFUNDED
            winning_team TEXT,
            merkle_seal_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            disbursed_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS token_transactions (
            tx_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            amount INTEGER NOT NULL,
            type TEXT NOT NULL, -- ESCROW_PAYOUT, PERK_PURCHASE, MATCH_REWARD, REFERRAL_BONUS
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()
        print("✅ Escrow and Token Transaction tables initialized in vault.db!")

if __name__ == "__main__":
    apply_schema()