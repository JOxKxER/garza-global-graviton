"""Real-time monitor for the encrypted Android telemetry gateway vault."""

from __future__ import annotations

import argparse
import base64
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


DEFAULT_VAULT_DIR = Path("sensory_telemetry_gateway_vault")
SALT_FILE = "telemetry_vault.salt"
RECORDS_FILE = "telemetry_records.jsonl.enc"


def format_bytes(value: int) -> str:
    if value < 1024:
        return f"{value} B"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value / (1024 * 1024):.1f} MB"


def derive_vault_key(passphrase: str, salt: bytes) -> bytes:
    derived = __import__("hashlib").pbkdf2_hmac(
        "sha256",
        passphrase.encode("utf-8"),
        salt,
        390_000,
        dklen=32,
    )
    return base64.urlsafe_b64encode(derived)


class GatewayVaultReader:
    """Decrypt local gateway records and expose only sanitized aggregates."""

    def __init__(self, directory: Path, passphrase: str) -> None:
        self.directory = directory
        self.records_path = directory / RECORDS_FILE
        salt_path = directory / SALT_FILE
        if not salt_path.is_file():
            raise FileNotFoundError(f"Vault salt not found: {salt_path}")
        self.cipher = Fernet(
            derive_vault_key(passphrase, salt_path.read_bytes())
        )

    def snapshot(self) -> list[dict[str, Any]]:
        if not self.records_path.is_file():
            return []
        records = []
        for line in self.records_path.read_bytes().splitlines():
            if not line:
                continue
            try:
                record = self.cipher.decrypt(line)
            except InvalidToken as error:
                raise RuntimeError(
                    "Vault record authentication failed"
                ) from error
            records.append(self._sanitize(record))
        return records

    @staticmethod
    def _sanitize(raw_record: bytes) -> dict[str, Any]:
        import json

        value = json.loads(raw_record.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("vault record must be an object")
        packet_count = value.get("packet_count")
        total_bytes = value.get("total_bytes")
        digest = value.get("batch_digest_sha256")
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
            raise ValueError("invalid aggregate telemetry record")
        return {
            "packet_count": packet_count,
            "total_bytes": total_bytes,
            "digest": digest,
        }


class GatewayMonitor:
    """Poll file metadata and print newly appended telemetry records."""

    def __init__(
        self, reader: GatewayVaultReader, include_existing: bool
    ) -> None:
        self.reader = reader
        self.seen = 0 if include_existing else len(reader.snapshot())
        self.batch_number = 0
        self.packet_total = 0
        self.byte_total = 0
        self.rejected = 0
        self.last_signature: tuple[int, int] | None = None

    def poll(self) -> int:
        if not self.reader.records_path.exists():
            return 0
        stat = self.reader.records_path.stat()
        signature = (stat.st_mtime_ns, stat.st_size)
        if signature == self.last_signature:
            return 0
        self.last_signature = signature
        records = self.reader.snapshot()
        new_records = records[self.seen:]
        self.seen = len(records)
        for record in new_records:
            self.batch_number += 1
            self.packet_total += record["packet_count"]
            self.byte_total += record["total_bytes"]
            timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
            print(
                f"[{timestamp}] [BATCH {self.batch_number:04d}] "
                f"packets={record['packet_count']:>4} | "
                f"encrypted_batch={format_bytes(record['total_bytes']):>9} | "
                f"verification={record['digest'][:16]}...",
                flush=True,
            )
        return len(new_records)

    def summary(self) -> None:
        print(
            "\nTACTICAL STATUS | "
            f"batches={self.batch_number} | "
            f"packets={self.packet_total} | "
            f"aggregate_bytes={format_bytes(self.byte_total)} | "
            f"rejected={self.rejected}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Monitor newly written encrypted gateway telemetry records."
        )
    )
    parser.add_argument(
        "--vault-dir",
        type=Path,
        default=Path(
            os.getenv("GGG_GATEWAY_VAULT_DIR", str(DEFAULT_VAULT_DIR))
        ),
    )
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--include-existing", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.interval <= 0.0:
        raise ValueError("interval must be positive")
    if not (passphrase := os.getenv("GGG_VAULT_PASSPHRASE")):
        raise RuntimeError("Set GGG_VAULT_PASSPHRASE before monitoring")

    monitor = GatewayMonitor(
        GatewayVaultReader(args.vault_dir, passphrase),
        args.include_existing,
    )
    print(f"GARZA GLOBAL GRAVITON | vault={args.vault_dir}")
    print(
        "Monitoring sanitized Android aggregate telemetry. "
        "Press Ctrl+C to stop.\n"
    )
    try:
        while True:
            monitor.poll()
            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
    finally:
        monitor.summary()


if __name__ == "__main__":
    main()
