"""SQLite-backed store for commit-reveal submissions and single-use nonces.

Single-use enforcement is done with an atomic UPDATE ... WHERE guard rather
than a read-then-write check, so two concurrent requests racing to consume
the same nonce cannot both succeed (classic TOCTOU bug in naive
"check flag, then set flag" implementations).
"""

from __future__ import annotations

import secrets
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS submissions (
    commitment_id TEXT PRIMARY KEY,
    sample_commitment_hash TEXT NOT NULL,
    client_pubkey TEXT NOT NULL,
    nonce TEXT NOT NULL,
    nonce_consumed INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'PENDING',
    bundle_json TEXT,
    created_at TEXT NOT NULL,
    nonce_expires_at TEXT NOT NULL
);
"""


@dataclass
class SubmissionRecord:
    commitment_id: str
    sample_commitment_hash: str
    client_pubkey: str
    nonce: str
    nonce_consumed: bool
    status: str
    bundle_json: Optional[str]
    created_at: str
    nonce_expires_at: str


class SubmissionStore:
    """Thread-safe wrapper around a single SQLite file. One process only --
    for multi-instance deployments, swap this for Postgres with the same
    method signatures (the atomic-UPDATE pattern below maps directly to
    `UPDATE ... WHERE nonce_consumed = 0 RETURNING *`)."""

    def __init__(self, db_path: str, nonce_ttl_seconds: int = 900):
        self._lock = threading.Lock()
        self._nonce_ttl_seconds = nonce_ttl_seconds
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def create_submission(
        self, sample_commitment_hash: str, client_pubkey: str
    ) -> SubmissionRecord:
        commitment_id = str(uuid.uuid4())
        nonce = secrets.token_hex(16)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self._nonce_ttl_seconds)
        created_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        nonce_expires_at = expires_at.strftime("%Y-%m-%dT%H:%M:%SZ")

        with self._lock:
            self._conn.execute(
                "INSERT INTO submissions ("
                " commitment_id, sample_commitment_hash, client_pubkey, nonce,"
                " created_at, nonce_expires_at"
                ") VALUES (?, ?, ?, ?, ?, ?)",
                (
                    commitment_id,
                    sample_commitment_hash,
                    client_pubkey,
                    nonce,
                    created_at,
                    nonce_expires_at,
                ),
            )
            self._conn.commit()

        return SubmissionRecord(
            commitment_id=commitment_id,
            sample_commitment_hash=sample_commitment_hash,
            client_pubkey=client_pubkey,
            nonce=nonce,
            nonce_consumed=False,
            status="PENDING",
            bundle_json=None,
            created_at=created_at,
            nonce_expires_at=nonce_expires_at,
        )

    def get(self, commitment_id: str) -> Optional[SubmissionRecord]:
        with self._lock:
            row = self._conn.execute(
                "SELECT commitment_id, sample_commitment_hash, client_pubkey, nonce,"
                " nonce_consumed, status, bundle_json, created_at, nonce_expires_at"
                " FROM submissions WHERE commitment_id = ?",
                (commitment_id,),
            ).fetchone()
        if row is None:
            return None
        return SubmissionRecord(
            commitment_id=row[0],
            sample_commitment_hash=row[1],
            client_pubkey=row[2],
            nonce=row[3],
            nonce_consumed=bool(row[4]),
            status=row[5],
            bundle_json=row[6],
            created_at=row[7],
            nonce_expires_at=row[8],
        )

    def nonce_is_expired(self, record: SubmissionRecord) -> bool:
        expires_at = datetime.strptime(
            record.nonce_expires_at, "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expires_at

    def attach_bundle(self, commitment_id: str, bundle_json: str, quote_nonce: str) -> bool:
        """Atomically marks the nonce consumed and stores the bundle, but
        only if this submission's nonce matches `quote_nonce` and has not
        already been consumed. Returns False (no rows changed) on any
        mismatch, replay attempt, or unknown commitment_id."""
        with self._lock:
            cursor = self._conn.execute(
                "UPDATE submissions"
                " SET nonce_consumed = 1, status = 'READY', bundle_json = ?"
                " WHERE commitment_id = ? AND nonce = ? AND nonce_consumed = 0",
                (bundle_json, commitment_id, quote_nonce),
            )
            self._conn.commit()
            return cursor.rowcount == 1

    def mark_rejected(self, commitment_id: str, reason: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE submissions SET status = ? WHERE commitment_id = ?",
                (f"REJECTED: {reason}"[:200], commitment_id),
            )
            self._conn.commit()
