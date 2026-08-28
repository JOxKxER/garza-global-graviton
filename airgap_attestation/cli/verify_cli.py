#!/usr/bin/env python3
"""Client-side CLI: verify an AttestationBundle.json entirely offline.

No vendor source code, network access, or SDK installation is required --
only this script (or the `airgap_attestation` package it imports), the
vendor's pinned public key(s), and the bundle file the buyer received.

Usage:
    python verify_cli.py --bundle AttestationBundle.json \\
        --platform-pubkey 3b1c...ef  \\
        --nonce b0df2134cf0bc8cacb4105e08cfa23ac \\
        --ak-pubkey 9a01...cd \\
        --json

Exit codes:
    0  verification passed
    1  verification failed (see printed reasons / --json output)
    2  usage or input error (bad file, bad hex, etc.)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from airgap_attestation.proof_bundle import load_bundle
from airgap_attestation.verify_client import verify_bundle


def _read_hex_arg(value: str) -> bytes:
    """Accepts either a literal hex string or a path to a file containing one."""
    candidate = Path(value)
    text = candidate.read_text(encoding="utf-8").strip() if candidate.is_file() else value
    try:
        return bytes.fromhex(text.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"'{value}' is not valid hex: {exc}") from exc


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verify_cli",
        description="Offline verifier for zero-network-leakage AttestationBundle files.",
    )
    parser.add_argument("--bundle", required=True, type=Path, help="Path to AttestationBundle.json")
    parser.add_argument(
        "--platform-pubkey",
        required=True,
        type=_read_hex_arg,
        help="Vendor's pinned Ed25519 public key, as hex or a path to a hex file",
    )
    parser.add_argument(
        "--nonce",
        type=_read_hex_arg,
        default=None,
        help="The nonce you originally issued for this submission (strongly recommended)",
    )
    parser.add_argument(
        "--ak-pubkey",
        action="append",
        dest="ak_pubkeys",
        type=_read_hex_arg,
        default=None,
        help="Pinned hardware Attestation Key public key(s); may be repeated",
    )
    parser.add_argument(
        "--allow-software-reference",
        action="store_true",
        help="DEV/TEST ONLY: accept non-hardware-rooted reference quotes",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON output")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if not args.bundle.is_file():
        print(f"error: bundle file not found: {args.bundle}", file=sys.stderr)
        return 2

    try:
        bundle = load_bundle(str(args.bundle))
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"error: could not parse bundle file: {exc}", file=sys.stderr)
        return 2

    result = verify_bundle(
        bundle,
        trusted_platform_pubkey=args.platform_pubkey,
        expected_nonce=args.nonce,
        trusted_ak_pubkeys=args.ak_pubkeys,
        reject_software_reference_quotes=not args.allow_software_reference,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        print(f"Bundle:   {args.bundle}")
        print(f"Bundle ID: {bundle.bundle_id}")
        print(f"Manifest:  {bundle.manifest.manifest_id} ({bundle.manifest.leaf_count} events)")
        print()
        for name, ok in result.checks.items():
            print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        if result.reasons:
            print("\nDetails:")
            for reason in result.reasons:
                print(f"  - {reason}")
        print()
        print("RESULT:", "PASSED" if result.passed else "FAILED")

    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
