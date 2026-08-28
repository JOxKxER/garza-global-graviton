"""Air-gap execution attestation toolkit.

This package implements the cryptographic building blocks described in the
"Zero-Network-Leakage Attestation Protocol": a domain-separated Merkle audit
log, Ed25519 platform signing, pluggable hardware-root-of-trust attestation
(TPM 2.0 / secure enclave), and a fully offline client-side verifier.

Nothing in this package requires the vendor's proprietary pipeline source to
be shared with a client -- the verifier only needs the published schema,
the platform's public signing key, and the attestation bundle produced for a
specific submission.
"""

from .merkle import MerkleTree
from .schemas import (
    SubmissionCommitment,
    ExecutionEvent,
    AuditManifest,
    TpmQuoteEvidence,
    AttestationBundle,
    VerificationResult,
)

__all__ = [
    "MerkleTree",
    "SubmissionCommitment",
    "ExecutionEvent",
    "AuditManifest",
    "TpmQuoteEvidence",
    "AttestationBundle",
    "VerificationResult",
]
