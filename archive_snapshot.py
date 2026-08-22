import sqlite3
import csv
import json
from datetime import datetime
from pathlib import Path

archive_dir = Path("audit_snapshots")
archive_dir.mkdir(exist_ok=True)

ts_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
csv_path = archive_dir / f"ledger_snapshot_{ts_str}.csv"
json_path = archive_dir / f"ledger_snapshot_{ts_str}.json"

conn = sqlite3.connect("cluster_ledger.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT * FROM orders ORDER BY created_at ASC")
rows = [dict(r) for r in cur.fetchall()]
conn.close()

# Write CSV
if rows:
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

# Write JSON
with open(json_path, "w", encoding="utf-8") as f:
    json.dump({"snapshot_time": ts_str, "total_records": len(rows), "records": rows}, f, indent=2)

print(f"[ARCHIVE SUCCESS] {len(rows)} immutable records written to {csv_path.name} & {json_path.name}")
