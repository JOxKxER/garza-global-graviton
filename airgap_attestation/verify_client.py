"""Fully offline client-side verifier.

A client needs exactly three things to run this -- none of which touch the
vendor's proprietary pipeline code:

  1. This module (or the published open-source verification package).
  2. The vendor's pinned Ed25519 platform public key (obtained once, out of
     band, e.g. printed in the master services agreement).
  3. The AttestationBundle JSON produced for their specific submission.

`verify_bundle()` re-derives every claim from first principles instead of
trusting any vendor-reported summary field.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from . import signing
from .merkle import MerkleTree
from .schemas import AttestationBundle, EventType, VerificationResult

# Payload keys that, if ever non-zero/non-empty, indicate network activity.
_NETWORK_EVIDENCE_KEYS = {
    "interfaces_up_non_loopback_count",
    "active_inet_sockets_count",
}
_NETWORK_SYSCALL_NAMES = {"socket", "connect", "sendto", "sendmsg", "bind", "recvfrom"}


def verify_bundle(
    bundle: AttestationBundle,
    trusted_platform_pubkey: bytes,
    expected_nonce: Optional[bytes] = None,
    trusted_ak_pubkeys: Optional[List[bytes]] = None,
    reject_software_reference_quotes: bool = True,
) -> VerificationResult:
    checks: Dict[str, bool] = {}
    reasons: List[str] = []

    # 1. Platform key must match the client's pinned trust anchor.
    checks["platform_pubkey_matches_pinned"] = (
        bundle.platform_pubkey == trusted_platform_pubkey.hex()
    )
    if not checks["platform_pubkey_matches_pinned"]:
        reasons.append(
            "Bundle's platform_pubkey does not match the pinned vendor key; "
            "refusing to trust any further claims in this bundle."
        )

    # 2. Platform signature over the bundle digest must verify.
    checks["platform_signature_valid"] = signing.verify(
        trusted_platform_pubkey,
        bundle.signable_digest_input(),
        bytes.fromhex(bundle.platform_signature),
    )
    if not checks["platform_signature_valid"]:
        reasons.append("Platform Ed25519 signature over the bundle digest is invalid.")

    # 3. Merkle root must match the events actually included in the manifest.
    leaves = [event.canonical_bytes() for event in bundle.manifest.events]
    try:
        recomputed_root = MerkleTree(leaves).root.hex()
    except ValueError:
        recomputed_root = ""
    checks["merkle_root_matches_events"] = recomputed_root == bundle.manifest.merkle_root
    if not checks["merkle_root_matches_events"]:
        reasons.append(
            "Recomputed Merkle root does not match manifest.merkle_root; the "
            "event log has been altered, reordered, or truncated after sealing."
        )

    # 4. Hardware quote must bind (nonce || merkle_root) and be internally consistent.
    quote = bundle.tpm_quote
    expected_quoted_data = bytes.fromhex(quote.nonce) + bytes.fromhex(bundle.manifest.merkle_root)
    checks["quote_binds_current_merkle_root"] = (
        bytes.fromhex(quote.quoted_data) == expected_quoted_data
    )
    if not checks["quote_binds_current_merkle_root"]:
        reasons.append("TPM/enclave quote does not bind this bundle's Merkle root.")

    if expected_nonce is not None:
        checks["nonce_matches_challenge"] = quote.nonce == expected_nonce.hex()
        if not checks["nonce_matches_challenge"]:
            reasons.append(
                "Quote nonce does not match the challenge this client issued; "
                "possible replay of an older attestation."
            )
    else:
        checks["nonce_matches_challenge"] = False
        reasons.append(
            "No expected_nonce supplied: cannot rule out replay of a prior "
            "attestation. Always issue a fresh nonce per submission."
        )

    checks["quote_is_hardware_rooted"] = not (
        reject_software_reference_quotes
        and quote.quote_format == "SOFTWARE_REFERENCE_ONLY_NOT_HARDWARE_ROOTED"
    )
    if not checks["quote_is_hardware_rooted"]:
        reasons.append(
            "Quote was produced by the software reference attestor, which is "
            "not hardware-rooted and must not be accepted for a real purchase decision."
        )

    if trusted_ak_pubkeys is not None:
        ak_pubkey_hex = quote.ak_certificate  # simplified: real impl parses X.509/CBOR
        checks["ak_certificate_chains_to_trust_root"] = any(
            ak_pubkey_hex == pk.hex() for pk in trusted_ak_pubkeys
        )
        if not checks["ak_certificate_chains_to_trust_root"]:
            reasons.append(
                "Attestation Key certificate does not chain to a pinned trust root "
                "(OEM TPM CA, or the enclave vendor's DCAP/Nitro root)."
            )
    else:
        checks["ak_certificate_chains_to_trust_root"] = False
        reasons.append(
            "No trusted_ak_pubkeys supplied: AK certificate chain was not validated."
        )

    # 5. Validity window: reject stale or not-yet-valid bundles.
    now = datetime.now(timezone.utc)
    created_at = _parse_iso(bundle.created_at)
    expires_at = _parse_iso(bundle.expires_at)
    checks["bundle_within_validity_window"] = created_at <= now <= expires_at
    if not checks["bundle_within_validity_window"]:
        reasons.append(
            f"Bundle is outside its validity window ({bundle.created_at} - "
            f"{bundle.expires_at}); request a fresh attestation instead of "
            "trusting an expired one."
        )

    # 6. The core business claim: zero observed network activity anywhere in the log.
    network_violations = _find_network_violations(bundle)
    checks["zero_network_activity_observed"] = len(network_violations) == 0
    reasons.extend(network_violations)

    passed = all(checks.values())
    return VerificationResult(passed=passed, checks=checks, reasons=reasons)


def _find_network_violations(bundle: AttestationBundle) -> List[str]:
    violations: List[str] = []
    for event in bundle.manifest.events:
        if event.event_type == EventType.NET_IFACE_SNAPSHOT:
            for key in _NETWORK_EVIDENCE_KEYS:
                value = event.payload.get(key)
                if isinstance(value, int) and value > 0:
                    violations.append(
                        f"seq {event.seq}: network evidence '{key}'={value} at {event.timestamp}"
                    )
        elif event.event_type == EventType.SYSCALL_SNAPSHOT:
            counts = event.payload.get("counts", {})
            for name in _NETWORK_SYSCALL_NAMES:
                value = counts.get(name)
                if isinstance(value, int) and value > 0:
                    violations.append(
                        f"seq {event.seq}: network syscall '{name}' count={value} at {event.timestamp}"
                    )
    return violations


def _parse_iso(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
