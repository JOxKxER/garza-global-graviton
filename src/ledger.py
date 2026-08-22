import sqlite3
import json
import time
from pathlib import Path
from typing import List, Dict, Any

DB_PATH = Path(__file__).resolve().parent.parent / "output" / "consensus_ledger.db"

class ConsensusLedger:
    def __init__(self, db_path: str = None):
        self.db_path = DB_PATH if db_path is None else Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.commit_count = 0
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS batches (
                    batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    merkle_root TEXT NOT NULL,
                    elements_count INTEGER NOT NULL,
                    worker_count INTEGER NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS node_proofs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id INTEGER NOT NULL,
                    worker_id TEXT NOT NULL,
                    task_id INTEGER NOT NULL,
                    block_hash TEXT NOT NULL,
                    latency_ms REAL NOT NULL,
                    metadata_json TEXT,
                    FOREIGN KEY(batch_id) REFERENCES batches(batch_id)
                )
            ''')
            conn.commit()
        finally:
            conn.close()

    def record_batch(
        self,
        merkle_root: str,
        elements_count: int,
        worker_proofs: List[Dict[str, Any]]
    ) -> int:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            now = time.time()
            cursor.execute(
                '''
                INSERT INTO batches (timestamp, merkle_root, elements_count, worker_count)
                VALUES (?, ?, ?, ?)
                ''',
                (now, merkle_root, elements_count, len(worker_proofs))
            )
            batch_id = cursor.lastrowid

            for proof in worker_proofs:
                cursor.execute(
                    '''
                    INSERT INTO node_proofs (batch_id, worker_id, task_id, block_hash, latency_ms, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        batch_id,
                        proof["worker_id"],
                        proof["task_id"],
                        proof["block_hash"],
                        proof["latency_ms"],
                        json.dumps(proof.get("metadata", {}))
                    )
                )
            conn.commit()

            # Perform periodic WAL checkpoint every 100 batches to keep database compact
            self.commit_count += 1
            if self.commit_count % 100 == 0:
                conn.execute("PRAGMA wal_checkpoint(PASSIVE);")

            return batch_id
        finally:
            conn.close()
