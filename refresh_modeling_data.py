"""Harvest permitted public modeling feeds for the local sports dashboard."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from sports_modeling import PublicDataHarvester, PublicDataSource


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "sports_modeling_data.json"
DEFAULT_CONFIG = ROOT / "sports_modeling_sources.json"


def load_sources(path: Path) -> list[PublicDataSource]:
    """Load enabled public source definitions from JSON."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    sources = []
    for item in payload.get("sources", []):
        if not item.get("enabled", True):
            continue
        sources.append(PublicDataSource(
            name=item["name"],
            url=item["url"],
            kind=item["kind"],
            params=item.get("params", {}),
            headers=item.get("headers", {}),
        ))
    return sources


def shape_payload(collected: dict[str, Any]) -> dict[str, Any]:
    """Keep a stable dashboard modeling document while retaining source data."""
    output: dict[str, Any] = {
        "games": collected.get("games", []),
        "injuries": collected.get("injuries", []),
        "sentiment": collected.get("sentiment", []),
        "player_statistics": collected.get("player_statistics", []),
        "coach_statistics": collected.get("coach_statistics", []),
        "harvested_kinds": sorted(collected),
    }
    return output


async def refresh(config_path: Path, output_path: Path) -> int:
    sources = load_sources(config_path)
    if not sources:
        raise ValueError("no enabled public modeling sources configured")
    harvester = PublicDataHarvester(
        timeout_seconds=20,
        requests_per_second=1.0,
        max_retries=3,
    )
    collected = await harvester.collect(sources)
    if not collected:
        raise RuntimeError("all public modeling sources failed")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(shape_payload(collected), indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output_path)
    print(f"Wrote modeling data kinds {sorted(collected)} to {output_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        return asyncio.run(refresh(args.config, args.output))
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, RuntimeError) as error:
        print(f"Modeling data refresh failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
