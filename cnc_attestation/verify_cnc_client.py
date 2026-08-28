#!/usr/bin/env python3
"""Offline, standalone CLI verifier for CNC job attestation bundles.

A buyer needs exactly three things -- no vendor SDK, no proprietary
toolpath-viewer software, no network access:
  1. This file (or the cnc_attestation/ package it lives in).
  2. The vendor's pinned controller (secure element) public key.
  3. The CncAttestationBundle.json produced for their specific job.

Usage:
    python verify_cnc_client.py --bundle CncAttestationBundle.json \\
        --controller-pubkey <hex or path> \\
        --nonce <hex you originally issued> \\
        --trusted-firmware-hash <hex sha256 of an approved firmware build> \\
        [--json]

Exit codes:
    0  verification passed
    1  verification failed (see printed reasons)
    2  usage or input error
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Set

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cnc_attestation.controller_quote import (
    load_bundle,
    validate_firmware_hash,
    validate_isolation_flags,
    verify_merkle_root_matches_manifest,
    verify_quote_signature,
    verify_quoted_data_binding,
)


def _read_hex_arg(value: str) -> bytes:
    candidate = Path(value)
    text = candidate.read_text(encoding="utf-8").strip() if candidate.is_file() else value
    try:
        return bytes.fromhex(text.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"'{value}' is not valid hex: {exc}") from exc


def _parse_iso(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verify_cnc_client",
        description="Offline verifier for CNC air-gapped job attestation bundles.",
    )
    parser.add_argument("--bundle", required=True, type=Path, help="Path to CncAttestationBundle.json")
    parser.add_argument(
        "--controller-pubkey",
        required=True,
        type=_read_hex_arg,
        help="Vendor's pinned secure-element Ed25519 public key, hex or a file path",
    )
    parser.add_argument(
        "--nonce",
        type=_read_hex_arg,
        default=None,
        help="The nonce you originally issued for this job (strongly recommended)",
    )
    parser.add_argument(
        "--trusted-firmware-hash",
        action="append",
        dest="trusted_firmware_hashes",
        default=None,
        help="hex sha256 of an approved controller firmware build; may be repeated",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON output")
    return parser


def verify(
    bundle,
    trusted_controller_pubkey: bytes,
    expected_nonce: Optional[bytes],
    trusted_firmware_hashes: Optional[Set[str]],
) -> dict:
    checks = {}
    reasons: List[str] = []

    checks["merkle_root_matches_manifest"] = verify_merkle_root_matches_manifest(bundle)
    if not checks["merkle_root_matches_manifest"]:
        reasons.append(
            "Recomputed Merkle root does not match the manifest/quote; the "
            "execution log was altered, reordered, or truncated after sealing."
        )

    checks["quote_signature_valid"] = verify_quote_signature(bundle.quote, trusted_controller_pubkey)
    if not checks["quote_signature_valid"]:
        reasons.append(
            "Controller quote signature is invalid or was not signed by the "
            "pinned secure-element public key."
        )

    checks["quote_binds_current_data"] = verify_quoted_data_binding(bundle.quote)
    if not checks["quote_binds_current_data"]:
        reasons.append("Quote's quoted_data does not equal nonce || merkle_root || firmware_hash.")

    if expected_nonce is not None:
        checks["nonce_matches_challenge"] = bundle.quote.nonce == expected_nonce.hex()
        if not checks["nonce_matches_challenge"]:
            reasons.append(
                "Quote nonce does not match the challenge you issued; possible "
                "replay of an older attestation."
            )
    else:
        checks["nonce_matches_challenge"] = False
        reasons.append("No --nonce supplied: cannot rule out replay of a prior attestation.")

    isolation_violations = validate_isolation_flags(bundle.quote)
    checks["serial_isolation_confirmed"] = len(isolation_violations) == 0
    reasons.extend(isolation_violations)

    checks["firmware_hash_trusted"] = validate_firmware_hash(bundle.quote, trusted_firmware_hashes)
    if trusted_firmware_hashes is None:
        reasons.append(
            "No --trusted-firmware-hash supplied: firmware provenance was not checked "
            f"(reported firmware_hash={bundle.quote.firmware_hash})."
        )
        checks["firmware_hash_trusted"] = False
    elif not checks["firmware_hash_trusted"]:
        reasons.append(
            f"Controller firmware_hash {bundle.quote.firmware_hash} is not in your trusted allowlist."
        )

    now = datetime.now(timezone.utc)
    created_at = _parse_iso(bundle.created_at)
    expires_at = _parse_iso(bundle.expires_at)
    checks["bundle_within_validity_window"] = created_at <= now <= expires_at
    if not checks["bundle_within_validity_window"]:
        reasons.append(
            f"Bundle is outside its validity window ({bundle.created_at} - {bundle.expires_at})."
        )

    passed = all(checks.values())
    return {"passed": passed, "checks": checks, "reasons": reasons}


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

    trusted_firmware_hashes = (
        set(h.lower() for h in args.trusted_firmware_hashes) if args.trusted_firmware_hashes else None
    )

    result = verify(
        bundle,
        trusted_controller_pubkey=args.controller_pubkey,
        expected_nonce=args.nonce,
        trusted_firmware_hashes=trusted_firmware_hashes,
    )

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Bundle:    {args.bundle}")
        print(f"Bundle ID: {bundle.bundle_id}")
        print(f"Job:       {bundle.manifest.manifest_id} ({bundle.manifest.leaf_count} events)")
        print()
        for name, ok in result["checks"].items():
            print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        if result["reasons"]:
            print("\nDetails:")
            for reason in result["reasons"]:
                print(f"  - {reason}")
        print()
        print("RESULT:", "PASSED" if result["passed"] else "FAILED")

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
