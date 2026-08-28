"""Assembles the final client-deliverable AttestationBundle: seals a
manifest's Merkle root into a hardware quote, then wraps the whole thing in
a platform Ed25519 signature so the bundle's integrity can be checked even
before the client validates the hardware trust chain."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from . import signing
from .attestation import HardwareAttestor
from .schemas import AttestationBundle, AuditManifest


def build_bundle(
    manifest: AuditManifest,
    attestor: HardwareAttestor,
    platform_private_key: bytes,
    platform_public_key: bytes,
    nonce: bytes,
    validity_window_seconds: int = 7 * 24 * 3600,
) -> AttestationBundle:
    merkle_root_bytes = bytes.fromhex(manifest.merkle_root)
    tpm_quote = attestor.quote(nonce=nonce, merkle_root=merkle_root_bytes)

    created_at = datetime.now(timezone.utc)
    expires_at = created_at + timedelta(seconds=validity_window_seconds)

    bundle = AttestationBundle(
        bundle_id=str(uuid.uuid4()),
        manifest=manifest,
        tpm_quote=tpm_quote,
        platform_pubkey=platform_public_key.hex(),
        platform_signature="",  # filled in below, after the rest is final
        created_at=created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        expires_at=expires_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    digest_input = bundle.signable_digest_input()
    bundle.platform_signature = signing.sign(platform_private_key, digest_input).hex()
    return bundle


def save_bundle(bundle: AttestationBundle, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bundle.to_dict(), f, indent=2, sort_keys=True)


def load_bundle(path: str) -> AttestationBundle:
    with open(path, "r", encoding="utf-8") as f:
        return AttestationBundle.from_dict(json.load(f))
