"""Standalone asynchronous telemetry collector for Garza Global Graviton.

The collector simulates manufacturing and sensor streams, processes batches in
threaded workers, computes Shannon entropy and Merkle roots, and appends each
record as an authenticated encrypted line in a local vault.

Set GGG_VAULT_PASSPHRASE for unattended runs. No telemetry leaves this machine.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import math
import os
import secrets
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from getpass import getpass
from pathlib import Path
from typing import Iterable, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


@dataclass(frozen=True)
class TelemetryBatch:
    batch_id: int
    source: str
    readings: tuple[float, ...]
    created_at: float


@dataclass(frozen=True)
class BatchReport:
    batch_id: int
    source: str
    reading_count: int
    entropy_bits: float
    merkle_root: str
    elapsed_ms: float


def derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a Fernet key with a per-vault salt."""
    derivation = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390_000,
    )
    derived = derivation.derive(passphrase.encode("utf-8"))
    return base64.urlsafe_b64encode(derived)


class EncryptedFileVault:
    """Append authenticated encrypted JSON records to a local file."""

    def __init__(self, directory: Path, passphrase: str) -> None:
        if not passphrase:
            raise ValueError("vault passphrase cannot be empty")
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.salt_path = directory / "telemetry_vault.salt"
        self.records_path = directory / "telemetry_records.jsonl.enc"
        if self.salt_path.exists():
            salt = self.salt_path.read_bytes()
        else:
            salt = secrets.token_bytes(16)
            self.salt_path.write_bytes(salt)
        self.cipher = Fernet(derive_key(passphrase, salt))

    def append(self, record: dict[str, object]) -> None:
        payload = json.dumps(
            record, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        with self.records_path.open("ab") as handle:
            handle.write(self.cipher.encrypt(payload) + b"\n")

    def read_all(self) -> list[dict[str, object]]:
        if not self.records_path.exists():
            return []
        return [
            json.loads(self.cipher.decrypt(line))
            for line in self.records_path.read_bytes().splitlines()
        ]


def shannon_entropy(values: Iterable[float]) -> float:
    """Calculate entropy over quantized readings."""
    buckets = Counter(round(value, 2) for value in values)
    if not (total := sum(buckets.values())):
        return 0.0
    return round(
        -sum(
            (count / total) * math.log2(count / total)
            for count in buckets.values()
        ),
        6,
    )


def merkle_root(values: Iterable[float]) -> str:
    """Build a duplicate-last SHA-256 Merkle tree for one batch."""
    leaves = [
        hashlib.sha256(f"{value:.6f}".encode("utf-8")).hexdigest()
        for value in values
    ]
    if not leaves:
        return hashlib.sha256(b"empty_batch").hexdigest()
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


def process_batch(batch: TelemetryBatch) -> BatchReport:
    started = time.perf_counter()
    return BatchReport(
        batch_id=batch.batch_id,
        source=batch.source,
        reading_count=len(batch.readings),
        entropy_bits=shannon_entropy(batch.readings),
        merkle_root=merkle_root(batch.readings),
        elapsed_ms=round((time.perf_counter() - started) * 1000, 3),
    )


async def simulated_stream(
    queue: asyncio.Queue[Optional[TelemetryBatch]],
    batch_count: int,
    batch_size: int,
    worker_count: int,
) -> None:
    """Produce simulated manufacturing telemetry with backpressure."""
    sources = ("assembly-line-a", "press-line-b", "thermal-cell-c")
    for batch_id in range(batch_count):
        readings = tuple(
            20.0
            + math.sin((batch_id * batch_size + index) / 8.0) * 2.5
            + ((index * 17 + batch_id) % 11) * 0.01
            for index in range(batch_size)
        )
        await queue.put(
            TelemetryBatch(
                batch_id=batch_id,
                source=sources[batch_id % len(sources)],
                readings=readings,
                created_at=time.time(),
            )
        )
    for _ in range(worker_count):
        await queue.put(None)


async def collect_telemetry(
    batch_count: int,
    batch_size: int,
    worker_count: int,
    vault: EncryptedFileVault,
) -> list[BatchReport]:
    """Ingest asynchronously and process batches on bounded thread workers."""
    queue: asyncio.Queue[Optional[TelemetryBatch]] = asyncio.Queue(
        maxsize=worker_count * 2
    )
    reports: list[BatchReport] = []
    producer = asyncio.create_task(
        simulated_stream(queue, batch_count, batch_size, worker_count)
    )

    with ThreadPoolExecutor(
        max_workers=worker_count,
        thread_name_prefix="ggg-telemetry",
    ) as pool:
        async def consume() -> None:
            while True:
                batch = await queue.get()
                if batch is None:
                    queue.task_done()
                    return
                report = await asyncio.get_running_loop().run_in_executor(
                    pool, process_batch, batch
                )
                vault.append(
                    {**report.__dict__, "created_at": batch.created_at}
                )
                reports.append(report)
                print(
                    f"[BATCH {report.batch_id:03d}] {report.source} | "
                    f"readings={report.reading_count:,} | "
                    f"entropy={report.entropy_bits:.3f} bits | "
                    f"merkle={report.merkle_root[:16]}... | "
                    f"{report.elapsed_ms:.3f} ms"
                )
                queue.task_done()

        consumers = [
            asyncio.create_task(consume()) for _ in range(worker_count)
        ]
        await producer
        await queue.join()
        await asyncio.gather(*consumers)
    return reports


def passphrase_from_environment() -> str:
    if value := os.getenv("GGG_VAULT_PASSPHRASE"):
        return value
    if not os.isatty(0):
        raise RuntimeError("Set GGG_VAULT_PASSPHRASE for non-interactive runs")
    return getpass("Vault passphrase: ")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect and encrypt simulated telemetry."
    )
    parser.add_argument("--batches", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, min(4, os.cpu_count() or 1)),
    )
    parser.add_argument(
        "--vault-dir", type=Path, default=Path("telemetry_vault")
    )
    args = parser.parse_args()
    if min(args.batches, args.batch_size, args.workers) < 1:
        raise ValueError("batches, batch-size, and workers must be positive")

    vault = EncryptedFileVault(args.vault_dir, passphrase_from_environment())
    started = time.perf_counter()
    reports = asyncio.run(
        collect_telemetry(args.batches, args.batch_size, args.workers, vault)
    )
    elapsed = time.perf_counter() - started
    reading_count = sum(report.reading_count for report in reports)
    print(
        f"Completed {len(reports)} batches / {reading_count:,} readings in "
        f"{elapsed:.3f}s using {args.workers} threaded workers."
    )
    print(f"Encrypted vault: {vault.records_path}")


if __name__ == "__main__":
    main()
