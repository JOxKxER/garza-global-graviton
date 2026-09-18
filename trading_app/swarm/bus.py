"""SQLite-backed message bus: the inter-process communication layer between
swarm bots.

Design choices, and why:

* WAL (Write-Ahead Logging) journal mode lets one writer and many readers
  proceed concurrently without blocking each other -- this is what actually
  delivers "zero race conditions or pipeline bottlenecks" here, rather than
  a hand-rolled file lock, which is easy to get subtly wrong.
* Messages are claimed with an atomic `UPDATE ... WHERE consumed_by IS NULL`
  (same pattern as airgap_attestation's single-use nonce store) so two
  consumer bots racing for the same topic can never both claim the same
  message -- one of the two UPDATEs will affect 0 rows.
* Shared state (e.g. the circuit-breaker tripped flag) is stored durably in
  its own table, not in a bot's in-memory object, specifically so that
  restarting one crashed bot can never silently reset a safety flag another
  bot depends on.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS bot_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    producer TEXT NOT NULL,
    created_at TEXT NOT NULL,
    consumed_by TEXT,
    consumed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_bot_messages_topic_unclaimed
    ON bot_messages(topic, consumed_by);

CREATE TABLE IF NOT EXISTS bot_heartbeats (
    bot_name TEXT PRIMARY KEY,
    last_seen_at TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bot_shared_state (
    state_key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Message:
    id: int
    topic: str
    payload: Dict[str, Any]
    producer: str
    created_at: str


class MessageBus:
    """One MessageBus instance per bot thread/process -- sqlite3 connections
    are not meant to be shared across threads, so each bot opens its own
    connection against the same on-disk WAL-mode database file."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        conn = sqlite3.connect(self.db_path, timeout=30)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    @property
    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            self._local.conn = conn
        return conn

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None

    # --- Pub/sub -----------------------------------------------------

    def publish(self, topic: str, payload: Dict[str, Any], producer: str) -> int:
        cursor = self._conn.execute(
            "INSERT INTO bot_messages (topic, payload_json, producer, created_at) VALUES (?, ?, ?, ?)",
            (topic, json.dumps(payload), producer, _now_iso()),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def consume(self, topic: str, consumer: str, limit: int = 10) -> List[Message]:
        """Atomically claims up to `limit` unclaimed messages on `topic` for
        `consumer`. Safe to call from multiple bots/threads concurrently --
        each message is claimed by exactly one caller."""
        candidate_ids = [
            row[0]
            for row in self._conn.execute(
                "SELECT id FROM bot_messages WHERE topic = ? AND consumed_by IS NULL ORDER BY id LIMIT ?",
                (topic, limit),
            )
        ]
        claimed: List[Message] = []
        for message_id in candidate_ids:
            cursor = self._conn.execute(
                "UPDATE bot_messages SET consumed_by = ?, consumed_at = ? "
                "WHERE id = ? AND consumed_by IS NULL",
                (consumer, _now_iso(), message_id),
            )
            self._conn.commit()
            if cursor.rowcount == 1:
                row = self._conn.execute(
                    "SELECT id, topic, payload_json, producer, created_at FROM bot_messages WHERE id = ?",
                    (message_id,),
                ).fetchone()
                claimed.append(
                    Message(id=row[0], topic=row[1], payload=json.loads(row[2]), producer=row[3], created_at=row[4])
                )
        return claimed

    def pending_count(self, topic: str) -> int:
        """Backlog depth for a topic -- the concrete signal the orchestrator
        uses to decide whether to scale up analytical workers."""
        row = self._conn.execute(
            "SELECT COUNT(*) FROM bot_messages WHERE topic = ? AND consumed_by IS NULL", (topic,)
        ).fetchone()
        return int(row[0])

    # --- Heartbeats ----------------------------------------------------

    def heartbeat(self, bot_name: str, status: str = "RUNNING") -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO bot_heartbeats (bot_name, last_seen_at, status) VALUES (?, ?, ?)",
            (bot_name, _now_iso(), status),
        )
        self._conn.commit()

    def status(self, bot_name: str) -> Optional[str]:
        row = self._conn.execute(
            "SELECT status FROM bot_heartbeats WHERE bot_name = ?", (bot_name,)
        ).fetchone()
        return row[0] if row else None

    def last_heartbeat(self, bot_name: str) -> Optional[float]:
        """Seconds since this bot's last heartbeat, or None if it has never
        reported one."""
        row = self._conn.execute(
            "SELECT last_seen_at FROM bot_heartbeats WHERE bot_name = ?", (bot_name,)
        ).fetchone()
        if row is None:
            return None
        last_seen = datetime.fromisoformat(row[0])
        return (datetime.now(timezone.utc) - last_seen).total_seconds()

    # --- Durable shared state (survives an individual bot restart) -----

    def set_shared_state(self, key: str, value: Any) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO bot_shared_state (state_key, value_json, updated_at) VALUES (?, ?, ?)",
            (key, json.dumps(value), _now_iso()),
        )
        self._conn.commit()

    def get_shared_state(self, key: str, default: Any = None) -> Any:
        row = self._conn.execute("SELECT value_json FROM bot_shared_state WHERE state_key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else default


def new_correlation_id() -> str:
    return uuid.uuid4().hex[:12]
