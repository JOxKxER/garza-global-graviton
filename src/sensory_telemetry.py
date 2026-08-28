"""PII-minimized sensory telemetry ingestion for the local proof of concept."""

from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from typing import Any

from telemetry_collector import EncryptedFileVault


ALLOWED_EVENT_TYPES = frozenset(
    {"touchstart", "touchend", "pointerdown", "pointerup", "click"}
)
MAX_EVENTS_PER_BATCH = 100
MAX_LATENCY_MS = 60_000.0


class SensoryTelemetryVault:
    """Validate, hash, and persist anonymous interaction batches."""

    def __init__(self, vault_directory: Path | None = None) -> None:
        directory = vault_directory or Path(
            os.getenv("GGG_SENSORY_VAULT_DIR", "sensory_telemetry_vault")
        )
        self._vault: EncryptedFileVault | None = None
        self._vault_directory = directory
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="ggg-sensory-vault",
        )
        self._lock = Lock()
        self.accepted_batches = 0
        self.rejected_batches = 0
        self.last_batch_hash: str | None = None

    def _get_vault(self) -> EncryptedFileVault:
        if self._vault is None:
            if not (passphrase := os.getenv("GGG_VAULT_PASSPHRASE")):
                raise RuntimeError("GGG_VAULT_PASSPHRASE is not configured")
            self._vault = EncryptedFileVault(self._vault_directory, passphrase)
        return self._vault

    @staticmethod
    def _number(value: Any, minimum: float, maximum: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("metric must be numeric")
        number = float(value)
        if not minimum <= number <= maximum:
            raise ValueError("metric is outside the allowed range")
        return round(number, 3)

    def sanitize_events(self, events: Any) -> list[dict[str, Any]]:
        """Keep bounded numeric metrics and discard all free text."""
        try:
            if (
                not isinstance(events, list)
                or not events
                or len(events) > MAX_EVENTS_PER_BATCH
            ):
                raise ValueError("events must contain 1 to 100 items")
            sanitized = []
            for event in events:
                if (
                    not isinstance(event, dict)
                    or event.get("type") not in ALLOWED_EVENT_TYPES
                ):
                    raise ValueError("unsupported event type")
                sanitized.append(
                    {
                        "type": event["type"],
                        "latency_ms": self._number(
                            event.get("latency_ms"), 0.0, MAX_LATENCY_MS
                        ),
                        "x": self._number(event.get("x", 0.0), 0.0, 1.0),
                        "y": self._number(event.get("y", 0.0), 0.0, 1.0),
                    }
                )
            return sanitized
        except ValueError:
            with self._lock:
                self.rejected_batches += 1
            raise

    @staticmethod
    def merkle_root(events: list[dict[str, Any]]) -> str:
        leaves = [
            hashlib.sha256(
                json.dumps(
                    event, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest()
            for event in events
        ]
        while len(leaves) > 1:
            if len(leaves) % 2:
                leaves.append(leaves[-1])
            leaves = [
                hashlib.sha256(
                    (leaves[index] + leaves[index + 1]).encode("utf-8")
                ).hexdigest()
                for index in range(0, len(leaves), 2)
            ]
        return leaves[0]

    def submit(self, payload: Any) -> tuple[dict[str, Any], Future[None]]:
        raw_events = (
            payload.get("events") if isinstance(payload, dict) else None
        )
        events = self.sanitize_events(raw_events)
        self._get_vault()
        root = self.merkle_root(events)
        record = {
            "schema": "ggg.sensory.v1",
            "event_count": len(events),
            "events": events,
            "merkle_root": root,
        }
        future = self._executor.submit(self._write_record, record)
        with self._lock:
            self.accepted_batches += 1
            self.last_batch_hash = root
        response = {
            "status": "accepted",
            "event_count": len(events),
            "merkle_root": root,
        }
        return response, future

    def _write_record(self, record: dict[str, Any]) -> None:
        self._get_vault().append(record)

    def record_failure(self) -> None:
        with self._lock:
            self.rejected_batches += 1

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "accepted_batches": self.accepted_batches,
                "rejected_batches": self.rejected_batches,
                "last_batch_hash": self.last_batch_hash,
            }

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True)
