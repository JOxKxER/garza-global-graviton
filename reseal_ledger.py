import sqlite3
import hashlib
from pathlib import Path

DB_PATH = Path('cluster_ledger.db')

def compute_hash(order_id, batch, client, count):
    raw = f'{order_id}_{batch}_{client}_{count}'.encode()
    return hashlib.sha256(raw).hexdigest()

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute('SELECT order_id, client_ref, element_count, settled_batch FROM orders')
rows = cur.fetchall()

updated = 0
for r in rows:
    batch = r['settled_batch'] if r['settled_batch'] is not None else 2650
    correct_hash = compute_hash(r['order_id'], batch, r['client_ref'], r['element_count'])
    cur.execute(
        'UPDATE orders SET settled_batch = ?, merkle_root = ? WHERE order_id = ?',
        (batch, correct_hash, r['order_id'])
    )
    updated += 1

conn.commit()
conn.close()
print(f'SUCCESS: Re-sealed {updated} historical ledger records to standard SHA-256.')
