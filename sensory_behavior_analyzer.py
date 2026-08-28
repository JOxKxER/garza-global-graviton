"""Offline behavioral pacing analysis for anonymous sensory telemetry.

This script decrypts the latest sensory batches locally, extracts only numeric
latency measurements, and sends aggregate metrics to a local Ollama instance.
No identifiers, timestamps, hashes, coordinates, source names, or raw events
are included in the prompt or transmitted.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from telemetry_collector import EncryptedFileVault


OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.1"
MAX_LATENCY_MS = 60_000.0


def entropy(values: Iterable[float]) -> float:
    """Calculate Shannon entropy over bounded, hundredth-ms buckets."""
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


def extract_metrics(
    records: list[dict[str, Any]], batch_limit: int
) -> dict[str, Any]:
    """Extract aggregate latency metrics without retaining record metadata."""
    if batch_limit < 1:
        raise ValueError("batch_limit must be positive")
    latencies = []
    for record in records[-batch_limit:]:
        events = record.get("events")
        if not isinstance(events, list):
            continue
        for event in events:
            if not isinstance(event, dict):
                continue
            value = event.get("latency_ms")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            numeric_value = float(value)
            if (
                math.isfinite(numeric_value)
                and 0.0 <= numeric_value <= MAX_LATENCY_MS
            ):
                latencies.append(min(numeric_value, MAX_LATENCY_MS))

    normalized = [round(value / MAX_LATENCY_MS, 6) for value in latencies]
    return {
        "batch_count": min(batch_limit, len(records)),
        "interaction_count": len(normalized),
        "latency_entropy_bits": entropy(latencies),
        "normalized_latencies": normalized,
        "average_normalized_latency": round(
            sum(normalized) / len(normalized), 6
        ) if normalized else 0.0,
        "min_normalized_latency": min(normalized, default=0.0),
        "max_normalized_latency": max(normalized, default=0.0),
    }


def build_prompt(metrics: dict[str, Any]) -> str:
    """Build a prompt containing aggregate numeric metrics only."""
    metrics_json = json.dumps(metrics, sort_keys=True, separators=(",", ":"))
    return (
        "You are an offline behavioral pacing analyst. "
        "Review only the following anonymous aggregate interaction metrics. "
        "Do not infer identity, demographics, location, device, or personal "
        "data. Return a concise report with pacing patterns, engagement "
        "confidence limits, and three practical UX experiment suggestions. "
        "Do not request or mention identifiers. Metrics: "
        f"{metrics_json}"
    )


def request_ollama(prompt: str, model: str, timeout: float) -> str:
    """Send the aggregate prompt to local Ollama and return its report text."""
    payload = json.dumps(
        {"model": model, "prompt": prompt, "stream": False}
    ).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(
            "Local Ollama is unavailable at localhost:11434"
        ) from error
    except json.JSONDecodeError as error:
        raise RuntimeError("Local Ollama returned invalid JSON") from error

    report = body.get("response")
    if not isinstance(report, str) or not report.strip():
        raise RuntimeError("Local Ollama returned no analysis response")
    return report.strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze anonymous sensory telemetry with local Ollama."
    )
    parser.add_argument(
        "--vault-dir", type=Path, default=Path("sensory_telemetry_vault")
    )
    parser.add_argument("--batches", type=int, default=5)
    parser.add_argument(
        "--model", default=os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    if args.timeout <= 0.0:
        raise ValueError("timeout must be positive")

    passphrase = os.getenv("GGG_VAULT_PASSPHRASE")
    if not passphrase:
        raise RuntimeError("Set GGG_VAULT_PASSPHRASE before reading the vault")

    vault = EncryptedFileVault(args.vault_dir, passphrase)
    metrics = extract_metrics(vault.read_all(), args.batches)
    report = request_ollama(build_prompt(metrics), args.model, args.timeout)
    print(report)


if __name__ == "__main__":
    main()
