"""
syndication_worker.py - Downstream companion for advanced_pipeline.py.

Monitors ./assets_out for structured assets produced by the core processor,
applies final packaging/metadata tagging (a distribution ID, an integrity
checksum, and a syndicated_at timestamp), and moves the enriched asset into
a local distribution archive. Never mutates the original asset in place --
it reads it, wraps it, writes the enriched copy to the archive, then removes
the now-redundant source only after that write has succeeded.

A local SQLite ledger (syndication_state.db) prevents reprocessing the same
source filename twice.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import signal
import sqlite3
import time
from datetime import datetime, timezone

logging.basicConfig(
    filename="syndication_worker.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class SyndicationWorker:
    def __init__(
        self,
        watch_dir: str,
        archive_dir: str,
        quarantine_dir: str,
        db_path: str,
        distribution_tier: str = "local_archive",
        poll_interval_seconds: int = 5,
    ):
        self.watch_dir = watch_dir
        self.archive_dir = archive_dir
        self.quarantine_dir = quarantine_dir
        self.db_path = db_path
        self.distribution_tier = distribution_tier
        self.poll_interval_seconds = poll_interval_seconds
        self.running = True

        for d in (self.watch_dir, self.archive_dir, self.quarantine_dir):
            os.makedirs(d, exist_ok=True)
        self._init_db()

        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, self._handle_exit)

    def _handle_exit(self, signum, frame):
        logging.info("Shutdown signal received. Stopping syndication worker...")
        print("\n[syndication_worker] Graceful shutdown initiated...")
        self.running = False

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS syndication_ledger (
                    file_name TEXT PRIMARY KEY,
                    distribution_id TEXT,
                    status TEXT,
                    syndicated_timestamp TEXT,
                    archive_path TEXT
                )
                """
            )
            conn.commit()

    def _already_syndicated(self, cursor: sqlite3.Cursor, file_name: str) -> bool:
        cursor.execute("SELECT status FROM syndication_ledger WHERE file_name = ?", (file_name,))
        row = cursor.fetchone()
        return row is not None and row[0] == "SUCCESS"

    def _record_state(
        self, cursor: sqlite3.Cursor, conn: sqlite3.Connection, file_name: str,
        status: str, distribution_id: str = "", archive_path: str = "",
    ) -> None:
        cursor.execute(
            """
            INSERT OR REPLACE INTO syndication_ledger
                (file_name, distribution_id, status, syndicated_timestamp, archive_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (file_name, distribution_id, status, datetime.now(timezone.utc).isoformat(), archive_path),
        )
        conn.commit()

    def _package_asset(self, file_path: str, distribution_id: str) -> dict:
        with open(file_path, "rb") as f:
            raw_bytes = f.read()
        checksum = hashlib.sha256(raw_bytes).hexdigest()

        asset = json.loads(raw_bytes.decode("utf-8"))
        asset["syndication_metadata"] = {
            "distribution_id": distribution_id,
            "distribution_tier": self.distribution_tier,
            "syndicated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_checksum_sha256": checksum,
        }
        return asset

    def run_once(self) -> int:
        """Runs a single scan/package cycle. Returns the number of assets
        successfully syndicated."""
        if not os.path.exists(self.watch_dir):
            return 0

        syndicated = 0
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for file_name in os.listdir(self.watch_dir):
                if not self.running:
                    break
                if not file_name.endswith(".json"):
                    continue

                file_path = os.path.join(self.watch_dir, file_name)
                if not os.path.isfile(file_path) or self._already_syndicated(cursor, file_name):
                    continue

                distribution_id = f"dist_{int(time.time() * 1000)}_{file_name.rsplit('.', 1)[0]}"
                try:
                    enriched_asset = self._package_asset(file_path, distribution_id)
                    archive_path = os.path.join(self.archive_dir, file_name)
                    with open(archive_path, "w", encoding="utf-8") as f:
                        json.dump(enriched_asset, f, indent=2)

                    os.remove(file_path)  # safe: archive write already succeeded above
                    self._record_state(cursor, conn, file_name, "SUCCESS", distribution_id, archive_path)
                    logging.info(f"Syndicated {file_name} -> {archive_path} ({distribution_id})")
                    syndicated += 1
                except Exception as exc:
                    logging.error(f"Syndication failure on {file_name}: {exc}")
                    self._record_state(cursor, conn, file_name, "QUARANTINED", distribution_id)
                    shutil.move(file_path, os.path.join(self.quarantine_dir, file_name))

        return syndicated

    def run(self) -> None:
        print(f"[syndication_worker] Active. Watching {self.watch_dir} -> {self.archive_dir}")
        while self.running:
            try:
                self.run_once()
            except Exception as exc:  # noqa: BLE001 - top-level supervisor loop must not die
                logging.error(f"Critical syndication_worker loop exception: {exc}")

            for _ in range(self.poll_interval_seconds):
                if not self.running:
                    break
                time.sleep(1)

        print("[syndication_worker] Stopped.")


if __name__ == "__main__":
    WATCH_DIR = "./assets_out"
    ARCHIVE_DIR = "./distribution_archive"
    QUARANTINE_DIR = "./syndication_quarantine"
    DB_PATH = "./syndication_state.db"

    worker = SyndicationWorker(
        watch_dir=WATCH_DIR, archive_dir=ARCHIVE_DIR, quarantine_dir=QUARANTINE_DIR, db_path=DB_PATH
    )
    worker.run()
