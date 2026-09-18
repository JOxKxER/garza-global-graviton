"""
feed_generator.py - Autonomous ingestion companion for advanced_pipeline.py.

Polls a public, no-auth-required open data feed (USGS earthquake GeoJSON --
US government public-domain data, published specifically for machine
consumption) and writes each new record as an individual file into
./data_inbox so the downstream pipeline never starves.

If the network is unreachable (offline/air-gapped operation), this falls
back to emitting a local synthetic telemetry snapshot instead -- zero
external dependency required for the pipeline to keep having work to do.

A local SQLite ledger (feed_state.db) tracks which feed record IDs have
already been written, so repeated polls of the same (overlapping) feed
window don't re-emit duplicates.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import signal
import sqlite3
import time
from datetime import datetime, timezone

import requests

logging.basicConfig(
    filename="feed_generator.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# US Geological Survey earthquake feed: public domain, no API key, explicitly
# published for automated/machine consumption. See https://earthquake.usgs.gov/earthquakes/feed/
FEED_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"


class FeedGenerator:
    def __init__(
        self,
        output_dir: str,
        db_path: str,
        poll_interval_seconds: int = 60,
        request_timeout_seconds: int = 10,
    ):
        self.output_dir = output_dir
        self.db_path = db_path
        self.poll_interval_seconds = poll_interval_seconds
        self.request_timeout_seconds = request_timeout_seconds
        self.running = True

        os.makedirs(self.output_dir, exist_ok=True)
        self._init_db()

        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, self._handle_exit)

    def _handle_exit(self, signum, frame):
        logging.info("Shutdown signal received. Stopping feed generator...")
        print("\n[feed_generator] Graceful shutdown initiated...")
        self.running = False

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ingested_records (
                    record_id TEXT PRIMARY KEY,
                    source TEXT,
                    ingested_timestamp TEXT
                )
                """
            )
            conn.commit()

    def _already_ingested(self, cursor: sqlite3.Cursor, record_id: str) -> bool:
        cursor.execute("SELECT 1 FROM ingested_records WHERE record_id = ?", (record_id,))
        return cursor.fetchone() is not None

    def _mark_ingested(self, cursor: sqlite3.Cursor, conn: sqlite3.Connection, record_id: str, source: str) -> None:
        cursor.execute(
            "INSERT OR REPLACE INTO ingested_records (record_id, source, ingested_timestamp) VALUES (?, ?, ?)",
            (record_id, source, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()

    def _write_inbox_file(self, record_id: str, payload: dict) -> None:
        safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in record_id)
        # Write to a temp name first, then rename -- avoids advanced_pipeline.py
        # ever seeing a partially-written file mid-poll.
        final_path = os.path.join(self.output_dir, f"{safe_name}.json")
        tmp_path = final_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_path, final_path)

    def _fetch_feed(self) -> list:
        response = requests.get(FEED_URL, timeout=self.request_timeout_seconds)
        response.raise_for_status()
        data = response.json()
        return data.get("features", [])

    def _emit_synthetic_telemetry(self) -> None:
        """Offline fallback: local, zero-network telemetry snapshot so the
        pipeline always has something to process even fully air-gapped."""
        now = datetime.now(timezone.utc)
        record_id = f"synthetic_{now.strftime('%Y%m%dT%H%M%S%f')}"
        disk = shutil.disk_usage(".")
        payload = {
            "record_id": record_id,
            "source": "synthetic_telemetry_fallback",
            "generated_at_utc": now.isoformat(),
            "telemetry": {
                "disk_total_bytes": disk.total,
                "disk_used_bytes": disk.used,
                "disk_free_bytes": disk.free,
                "process_id": os.getpid(),
            },
        }
        self._write_inbox_file(record_id, payload)
        logging.info(f"Emitted synthetic telemetry fallback record: {record_id}")

    def run_once(self) -> int:
        """Runs a single poll cycle. Returns the number of new files written.
        Exposed separately from run() so it can be exercised in a dry run/test
        without an infinite loop."""
        written = 0
        try:
            features = self._fetch_feed()
        except (requests.RequestException, ValueError) as exc:
            logging.warning(f"Feed fetch failed ({exc}); falling back to synthetic telemetry.")
            self._emit_synthetic_telemetry()
            return 1

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for feature in features:
                record_id = str(feature.get("id", ""))
                if not record_id or self._already_ingested(cursor, record_id):
                    continue
                self._write_inbox_file(record_id, feature)
                self._mark_ingested(cursor, conn, record_id, source="usgs_earthquake_feed")
                written += 1

        if written == 0:
            logging.info("Feed poll returned no new records; emitting synthetic telemetry to avoid starvation.")
            self._emit_synthetic_telemetry()
            written = 1

        logging.info(f"Feed poll cycle wrote {written} new file(s) to {self.output_dir}")
        return written

    def run(self) -> None:
        print(f"[feed_generator] Active. Polling every {self.poll_interval_seconds}s -> {self.output_dir}")
        while self.running:
            try:
                self.run_once()
            except Exception as exc:  # noqa: BLE001 - top-level supervisor loop must not die
                logging.error(f"Critical feed_generator loop exception: {exc}")

            for _ in range(self.poll_interval_seconds):
                if not self.running:
                    break
                time.sleep(1)

        print("[feed_generator] Stopped.")


if __name__ == "__main__":
    OUTPUT_DIR = "./data_inbox"
    DB_PATH = "./feed_state.db"
    POLL_INTERVAL_SECONDS = int(os.environ.get("FEED_POLL_INTERVAL_SECONDS", "60"))

    generator = FeedGenerator(
        output_dir=OUTPUT_DIR, db_path=DB_PATH, poll_interval_seconds=POLL_INTERVAL_SECONDS
    )
    generator.run()
