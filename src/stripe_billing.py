import os
import sqlite3
import uuid
from pathlib import Path

DB_PATH = Path('cluster_ledger.db')

# Pricing Matrix (Zero Overhead)
TIERS = {
    'starter': {'price_cents': 2900, 'credits': 1_000_000, 'label': 'Starter Shard (1M Elements)'},
    'pro':     {'price_cents': 9900, 'credits': 5_000_000, 'label': 'Professional Cluster (5M Elements)'},
    'enterprise': {'price_cents': 29900, 'credits': 20_000_000, 'label': 'Enterprise Sovereign (20M Elements)'}
}

def init_billing_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS customer_keys (
            api_key TEXT PRIMARY KEY,
            customer_email TEXT,
            remaining_credits INTEGER,
            tier TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_billing_db()

def provision_paid_key(email: str, tier: str) -> dict:
    if tier not in TIERS:
        tier = 'starter'
    new_key = f'ggg_live_{uuid.uuid4().hex[:12]}'
    credits = TIERS[tier]['credits']
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO customer_keys (api_key, customer_email, remaining_credits, tier, created_at) VALUES (?, ?, ?, ?, datetime(\"now\"))',
        (new_key, email, credits, tier)
    )
    conn.commit()
    conn.close()
    return {'api_key': new_key, 'credits_allocated': credits, 'tier': tier}
