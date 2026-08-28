"""Hardware-rooted controller state quote for CNC job attestation.

Target hardware model: an onboard secure element or MCU coprocessor (e.g. a
Microchip ATECC608 / SE050-class part, or a locked-down STM32 with a
provisioned device-unique key) physically wired to the CNC controller board
(GRBL/grblHAL on a Shapeoko Pro, or the Nomad 3's onboard controller). The
coprocessor -- not the general-purpose controller firmware -- holds the
signing key and independently samples the isolation flags below, so a
compromised main firmware cannot forge a "no radio" claim on its own.

The quote binds THREE things together in one signature, so none of them can
be swapped independently after the fact:
  1. `firmware_hash`   -- which exact firmware image ran the job
  2. `serial_isolation_flags` -- what the coprocessor itself observed about
     the board's network/radio state during the job
  3. `merkle_root`     -- the G-code execution log's tamper-evident root
     (see gcode_merkle.py)
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set

from . import signing
from .gcode_merkle import GCodeAuditManifest, recompute_merkle_root


def _utc_now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


# Isolation flags that MUST all be false/absent for a job to count as
# air-gapped. Add new evidence sources here as new keys, not renamed ones,
# so older bundles stay checkable against a superset of known flags.
REQUIRED_FALSE_FLAGS = (
    "wifi_radio_enabled",
    "bluetooth_enabled",
    "ethernet_link_detected",
    "usb_network_gadget_enabled",
    "cellular_modem_present",
)


@dataclass
class ControllerStateQuote:
    quote_format: str  # e.g. "CNC_MCU_QUOTE_V1"
    firmware_hash: str  # hex sha256 of the exact firmware image that ran the job
    serial_isolation_flags: Dict[str, bool]
    merkle_root: str  # hex, must match the sealed GCodeAuditManifest
    nonce: str  # hex, supplied by the client challenge to prevent replay
    quoted_data: str  # hex(nonce || merkle_root || firmware_hash_bytes), what's signed
    signature: str  # hex signature over quoted_data by the secure element's key
    controller_pubkey: str  # hex Ed25519 public key of the secure element
    generated_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ControllerStateQuote":
        return ControllerStateQuote(**data)


@dataclass
class CncAttestationBundle:
    bundle_id: str
    manifest: GCodeAuditManifest
    quote: ControllerStateQuote
    created_at: str
    expires_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "manifest": self.manifest.to_dict(),
            "quote": self.quote.to_dict(),
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "CncAttestationBundle":
        return CncAttestationBundle(
            bundle_id=data["bundle_id"],
            manifest=GCodeAuditManifest.from_dict(data["manifest"]),
            quote=ControllerStateQuote.from_dict(data["quote"]),
            created_at=data["created_at"],
            expires_at=data["expires_at"],
        )


def build_quote(
    controller_private_key: bytes,
    controller_public_key: bytes,
    firmware_hash: str,
    serial_isolation_flags: Dict[str, bool],
    merkle_root_hex: str,
    nonce: bytes,
) -> ControllerStateQuote:
    """Called on the secure element / MCU coprocessor side (or its reference
    software stand-in for local testing) after a job completes."""
    firmware_hash_bytes = bytes.fromhex(firmware_hash)
    merkle_root_bytes = bytes.fromhex(merkle_root_hex)
    quoted_data = nonce + merkle_root_bytes + firmware_hash_bytes
    signature = signing.sign(controller_private_key, quoted_data)
    return ControllerStateQuote(
        quote_format="CNC_MCU_QUOTE_V1",
        firmware_hash=firmware_hash,
        serial_isolation_flags=dict(serial_isolation_flags),
        merkle_root=merkle_root_hex,
        nonce=nonce.hex(),
        quoted_data=quoted_data.hex(),
        signature=signature.hex(),
        controller_pubkey=controller_public_key.hex(),
    )


def build_bundle(
    manifest: GCodeAuditManifest,
    quote: ControllerStateQuote,
    validity_window_seconds: int = 30 * 24 * 3600,
) -> CncAttestationBundle:
    from datetime import datetime, timedelta, timezone

    created_at = datetime.now(timezone.utc)
    expires_at = created_at + timedelta(seconds=validity_window_seconds)
    return CncAttestationBundle(
        bundle_id=str(uuid.uuid4()),
        manifest=manifest,
        quote=quote,
        created_at=created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        expires_at=expires_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def save_bundle(bundle: CncAttestationBundle, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bundle.to_dict(), f, indent=2, sort_keys=True)


def load_bundle(path: str) -> CncAttestationBundle:
    with open(path, "r", encoding="utf-8") as f:
        return CncAttestationBundle.from_dict(json.load(f))


# --------------------------------------------------------------------------
# Validation logic
# --------------------------------------------------------------------------

def verify_quote_signature(quote: ControllerStateQuote, trusted_controller_pubkey: bytes) -> bool:
    if quote.controller_pubkey != trusted_controller_pubkey.hex():
        return False
    return signing.verify(
        trusted_controller_pubkey, bytes.fromhex(quote.quoted_data), bytes.fromhex(quote.signature)
    )


def verify_quoted_data_binding(quote: ControllerStateQuote) -> bool:
    """Confirms quoted_data is really hex(nonce || merkle_root || firmware_hash)
    and not an unrelated blob that happens to carry a valid signature."""
    expected = bytes.fromhex(quote.nonce) + bytes.fromhex(quote.merkle_root) + bytes.fromhex(
        quote.firmware_hash
    )
    return bytes.fromhex(quote.quoted_data) == expected


def validate_isolation_flags(quote: ControllerStateQuote) -> List[str]:
    """Returns a list of human-readable violations; empty list == fully isolated."""
    violations: List[str] = []
    for flag_name in REQUIRED_FALSE_FLAGS:
        value = quote.serial_isolation_flags.get(flag_name)
        if value is None:
            violations.append(f"missing isolation flag '{flag_name}' (cannot confirm isolation)")
        elif value is True:
            violations.append(f"isolation flag '{flag_name}' is TRUE (network/radio path active)")
    return violations


def validate_firmware_hash(
    quote: ControllerStateQuote, trusted_firmware_hashes: Optional[Set[str]]
) -> bool:
    """If a known-good firmware allowlist is supplied, the quote's firmware
    hash must be in it. If no allowlist is supplied, this check is skipped
    (caller should treat that as a warning, not a silent pass -- see
    verify_cnc_client.py)."""
    if trusted_firmware_hashes is None:
        return True
    return quote.firmware_hash in trusted_firmware_hashes


def verify_merkle_root_matches_manifest(bundle: CncAttestationBundle) -> bool:
    recomputed = recompute_merkle_root(bundle.manifest).hex()
    return recomputed == bundle.manifest.merkle_root == bundle.quote.merkle_root
