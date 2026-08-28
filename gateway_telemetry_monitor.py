"""Live terminal monitor for the encrypted gateway telemetry vault."""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.fernet import InvalidToken

from telemetry_collector import EncryptedFileVault


DEFAULT_VAULT_DIR = Path("sensory_telemetry_gateway_vault")


def format_bytes(value: int) -> str:
    if value < 1024:
        return f"{value} B"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value / (1024 * 1024):.1f} MB"


def validate_record(record: Any) -> dict[str, Any] | None:
    """Return only safe aggregate fields from a decrypted vault record."""
    if not isinstance(record, dict):
        return None
    packet_count = record.get("packet_count")
    total_bytes = record.get("total_bytes")
    digest = record.get("batch_digest_sha256")
    if (
        isinstance(packet_count, bool)
        or not isinstance(packet_count, int)
        or packet_count < 1
        or isinstance(total_bytes, bool)
        or not isinstance(total_bytes, int)
        or total_bytes < 0
        or not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        return None
    return {
        "packet_count": packet_count,
        "total_bytes": total_bytes,
        "digest": digest,
    }


class GatewayTelemetryMonitor:
    """Poll and display newly appended encrypted gateway records."""

    def __init__(
        self, vault: EncryptedFileVault, include_existing: bool
    ) -> None:
        self.vault = vault
        self._seen = 0 if include_existing else len(vault.read_all())
        self.total_packets = 0
        self.total_bytes = 0
        self.valid_batches = 0
        self.invalid_batches = 0

    def poll(self) -> int:
        """Read new records and print one tactical line per valid batch."""
        try:
            records = self.vault.read_all()
        except (InvalidToken, ValueError, OSError) as error:
            print(
                f"[VAULT ERROR] Unable to decrypt/read vault: {error}",
                file=sys.stderr,
            )
            return 0

        new_records = records[self._seen:]
        self._seen = len(records)
        for record in new_records:
            safe_record = validate_record(record)
            if safe_record is None:
                self.invalid_batches += 1
                print("[REJECTED] Invalid aggregate telemetry record")
                continue
            self.valid_batches += 1
            self.total_packets += safe_record["packet_count"]
            self.total_bytes += safe_record["total_bytes"]
            timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
            print(
                f"[{timestamp}] [BATCH {self.valid_batches:04d}] "
                f"packets={safe_record['packet_count']:>4} | "
                f"encrypted_batch="
                f"{format_bytes(safe_record['total_bytes']):>9} | "
                f"digest={safe_record['digest'][:16]}..."
            )
        return len(new_records)

    def print_summary(self) -> None:
        print(
            "\nTACTICAL STATUS | "
            f"verified_batches={self.valid_batches} | "
            f"packets={self.total_packets} | "
            f"aggregate_bytes={format_bytes(self.total_bytes)} | "
            f"rejected={self.invalid_batches}"
        )


def get_passphrase() -> str:
    if not (passphrase := os.getenv("GGG_VAULT_PASSPHRASE")):
        raise RuntimeError(
            "Set GGG_VAULT_PASSPHRASE before monitoring the vault"
        )
    return passphrase


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Monitor encrypted gateway telemetry in real time."
    )
    parser.add_argument("--vault-dir", type=Path, default=DEFAULT_VAULT_DIR)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument(
        "--include-existing",
        action="store_true",
        help="Display records already present when monitoring starts",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Poll once and exit instead of following the vault",
    )
    args = parser.parse_args()
    if args.interval <= 0.0:
        raise ValueError("interval must be positive")

    vault = EncryptedFileVault(args.vault_dir, get_passphrase())
    monitor = GatewayTelemetryMonitor(vault, args.include_existing)
    print(f"GARZA GLOBAL GRAVITON | encrypted vault: {args.vault_dir}")
    print("Monitoring sanitized aggregate telemetry. Press Ctrl+C to stop.\n")
    try:
        while True:
            monitor.poll()
            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
    finally:
        monitor.print_summary()


if __name__ == "__main__":
    main()
