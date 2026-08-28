"""Wire-format data structures for the zero-network-leakage attestation
protocol. All timestamps are UTC ISO-8601. All binary values are represented
as lowercase hex strings once serialized, so bundles are plain JSON and can
be transported over any out-of-band channel (email, sealed USB media, paper
QR codes, etc.) without special encoding.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List


def _utc_now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class EventType(str, Enum):
    PROCESS_START = "PROCESS_START"
    SYSCALL_SNAPSHOT = "SYSCALL_SNAPSHOT"
    NET_IFACE_SNAPSHOT = "NET_IFACE_SNAPSHOT"
    RESOURCE_SNAPSHOT = "RESOURCE_SNAPSHOT"
    PROCESS_END = "PROCESS_END"
    ANOMALY = "ANOMALY"


@dataclass
class SubmissionCommitment:
    """Commit-reveal binding for a client's blinded test sample.

    The client hashes (sample_bytes || salt) and sends only the commitment
    hash plus an encrypted payload up front. The salt/key is delivered over a
    *separate* out-of-band channel and only revealed after execution, so the
    vendor cannot silently substitute a different sample, and the client
    cannot later deny which exact sample was tested.
    """

    commitment_id: str
    sample_commitment_hash: str  # hex sha256(sample_bytes || salt)
    client_pubkey: str  # hex Ed25519 public key, binds this commitment to the client
    created_at: str = field(default_factory=_utc_now_iso)

    def canonical_bytes(self) -> bytes:
        return _canonical_json(asdict(self))


@dataclass
class ExecutionEvent:
    """One entry in the tamper-evident execution log.

    `payload` only ever contains non-proprietary, aggregate/summary data
    (counters, category names, interface states) -- never raw process
    memory, file contents, or command-line arguments -- so the manifest can
    be handed to the client without an NDA review pass.
    """

    seq: int
    event_type: EventType
    timestamp: str
    payload: Dict[str, Any]

    def canonical_bytes(self) -> bytes:
        return _canonical_json(
            {
                "seq": self.seq,
                "event_type": self.event_type.value,
                "timestamp": self.timestamp,
                "payload": self.payload,
            }
        )


@dataclass
class AuditManifest:
    manifest_id: str
    commitment_id: str
    events: List[ExecutionEvent]
    merkle_root: str  # hex
    leaf_count: int
    sealed_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "commitment_id": self.commitment_id,
            "events": [
                {
                    "seq": e.seq,
                    "event_type": e.event_type.value,
                    "timestamp": e.timestamp,
                    "payload": e.payload,
                }
                for e in self.events
            ],
            "merkle_root": self.merkle_root,
            "leaf_count": self.leaf_count,
            "sealed_at": self.sealed_at,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AuditManifest":
        events = [
            ExecutionEvent(
                seq=e["seq"],
                event_type=EventType(e["event_type"]),
                timestamp=e["timestamp"],
                payload=e["payload"],
            )
            for e in data["events"]
        ]
        return AuditManifest(
            manifest_id=data["manifest_id"],
            commitment_id=data["commitment_id"],
            events=events,
            merkle_root=data["merkle_root"],
            leaf_count=data["leaf_count"],
            sealed_at=data["sealed_at"],
        )


@dataclass
class TpmQuoteEvidence:
    """A hardware-rooted quote binding (nonce, merkle_root) to a measured
    PCR state. In production this is produced by a physical TPM 2.0 chip
    (see attestation.py); the fields below match the shape of a real
    TPM2_Quote command's output so this schema does not need to change when
    swapping the reference software attestor for real hardware.
    """

    quote_format: str  # e.g. "TPM2_QUOTE_V1" or "SGX_DCAP_V1" or "NITRO_V1"
    pcr_selection: List[int]
    pcr_digest: str  # hex digest of the selected PCR bank at quote time
    nonce: str  # hex, supplied by the verifier/client to prevent replay
    quoted_data: str  # hex(nonce || merkle_root), the exact bytes the AK signed
    signature: str  # hex signature over quoted_data by the Attestation Key (AK)
    ak_certificate: str  # PEM/base64 certificate chaining the AK to a trust root
    generated_at: str = field(default_factory=_utc_now_iso)


@dataclass
class AttestationBundle:
    bundle_id: str
    manifest: AuditManifest
    tpm_quote: TpmQuoteEvidence
    platform_pubkey: str  # hex Ed25519 public key of the signing platform
    platform_signature: str  # hex Ed25519 signature over the bundle digest
    created_at: str
    expires_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "manifest": self.manifest.to_dict(),
            "tpm_quote": asdict(self.tpm_quote),
            "platform_pubkey": self.platform_pubkey,
            "platform_signature": self.platform_signature,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AttestationBundle":
        return AttestationBundle(
            bundle_id=data["bundle_id"],
            manifest=AuditManifest.from_dict(data["manifest"]),
            tpm_quote=TpmQuoteEvidence(**data["tpm_quote"]),
            platform_pubkey=data["platform_pubkey"],
            platform_signature=data["platform_signature"],
            created_at=data["created_at"],
            expires_at=data["expires_at"],
        )

    def signable_digest_input(self) -> bytes:
        """Bytes the platform key signs: binds the merkle root, the TPM quote
        signature, and the bundle's validity window together so none of them
        can be swapped independently without invalidating the signature."""
        return _canonical_json(
            {
                "bundle_id": self.bundle_id,
                "manifest_id": self.manifest.manifest_id,
                "merkle_root": self.manifest.merkle_root,
                "tpm_quoted_data": self.tpm_quote.quoted_data,
                "tpm_signature": self.tpm_quote.signature,
                "created_at": self.created_at,
                "expires_at": self.expires_at,
            }
        )


@dataclass
class VerificationResult:
    passed: bool
    checks: Dict[str, bool]
    reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _canonical_json(obj: Any) -> bytes:
    """Deterministic serialization so the same logical object always hashes
    / signs to the same bytes regardless of dict key insertion order."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
