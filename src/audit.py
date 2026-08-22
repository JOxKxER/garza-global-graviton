import sqlite3
import argparse
import json
import csv
from pathlib import Path
from src.core import MerkleTree

DB_PATH = Path(__file__).resolve().parent.parent / "output" / "consensus_ledger.db"

def run_ledger_audit(export_csv: str = None):
    if not DB_PATH.exists():
        print(f"[-] Ledger database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT batch_id, timestamp, merkle_root, elements_count, worker_count FROM batches ORDER BY batch_id ASC")
    batches = cursor.fetchall()

    print(f"\n=======================================================")
    print(f" 🛡️  GARZA GLOBAL GRAVITON - CRYPTOGRAPHIC LEDGER AUDIT")
    print(f"=======================================================")
    print(f"[*] Total Batches to Audit: {len(batches)}")

    verified_count = 0
    tampered_count = 0
    export_rows = []

    for b in batches:
        b_id = b["batch_id"]
        stored_root = b["merkle_root"]
        
        cursor.execute("SELECT worker_id, task_id, block_hash, latency_ms FROM node_proofs WHERE batch_id = ? ORDER BY task_id ASC", (b_id,))
        proofs = cursor.fetchall()

        leaf_hashes = [p["block_hash"] for p in proofs]
        reconstructed_tree = MerkleTree(leaf_hashes)

        is_valid = (reconstructed_tree.root_hash == stored_root)
        if is_valid:
            verified_count += 1
        else:
            tampered_count += 1

        export_rows.append({
            "batch_id": b_id,
            "timestamp": b["timestamp"],
            "elements_count": b["elements_count"],
            "worker_count": b["worker_count"],
            "merkle_root": stored_root,
            "audit_status": "PASS" if is_valid else "FAIL"
        })

    print(f"[+] Cryptographically Verified Batches : {verified_count}")
    print(f"[!] Tampered / Corrupt Batches         : {tampered_count}")
    print(f"[*] Ledger Integrity Status            : {'100% HEALTHY' if tampered_count == 0 else 'COMPROMISED'}")
    print(f"=======================================================\n")

    if export_csv:
        out_path = Path(export_csv)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["batch_id", "timestamp", "elements_count", "worker_count", "merkle_root", "audit_status"])
            writer.writeheader()
            writer.writerows(export_rows)
        print(f"[+] Full audit report exported to {out_path.resolve()}\n")

    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit Garza Global Graviton Cryptographic Ledger")
    parser.add_argument("--export-csv", type=str, default="output/audit_report.csv", help="Path to export CSV audit report")
    args = parser.parse_args()
    run_ledger_audit(export_csv=args.export_csv)
