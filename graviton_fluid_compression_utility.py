"""Graviton Fluid Compression Desktop Utility.

A small local demo that compresses and restores a text or binary file with
Python's standard-library gzip support. It does not upload user data.
"""

from __future__ import annotations

import argparse
import gzip
from pathlib import Path


def compress_file(source: Path, destination: Path) -> tuple[int, int]:
    raw = source.read_bytes()
    compressed = gzip.compress(raw)
    destination.write_bytes(compressed)
    restored = gzip.decompress(compressed)
    if restored != raw:
        raise ValueError("reconstruction check failed")
    return len(raw), len(compressed)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compress a local file safely."
    )
    parser.add_argument("source", type=Path, help="File to compress")
    parser.add_argument(
        "-o", "--output", type=Path, help="Compressed output file"
    )
    args = parser.parse_args()
    default_output = args.source.with_suffix(f"{args.source.suffix}.ggg.gz")
    output = args.output or default_output
    original, compressed = compress_file(args.source, output)
    ratio = original / compressed if compressed else 0.0
    print(f"Compressed {args.source} -> {output}")
    print(f"Original: {original:,} bytes | Compressed: {compressed:,} bytes")
    print(f"Storage ratio: {ratio:.2f}x")


if __name__ == "__main__":
    main()
