"""Lightweight Graviton Telemetry Client App.

Reads simple CSV telemetry locally and prints an easy-to-scan summary. The
client is offline by default and sends nothing without an explicit extension.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def summarize_csv(source: Path) -> dict[str, object]:
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    fields = list(rows[0]) if rows else []
    return {
        "file": str(source),
        "records": len(rows),
        "fields": fields,
        "latest_record": rows[-1] if rows else {},
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="View local telemetry simply."
    )
    parser.add_argument("csv_file", type=Path, help="CSV telemetry file")
    args = parser.parse_args()
    summary = summarize_csv(args.csv_file)
    print(f"Telemetry file: {summary['file']}")
    print(f"Records: {summary['records']}")
    print(f"Fields: {', '.join(summary['fields']) or 'none'}")
    print(f"Latest record: {summary['latest_record'] or 'none'}")


if __name__ == "__main__":
    main()
