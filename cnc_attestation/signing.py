"""Ed25519 signing helpers, standalone for the cnc_attestation package (no
dependency on the unrelated airgap_attestation product line)."""

from __future__ import annotations

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)


def generate_keypair() -> tuple[bytes, bytes]:
    """Returns (private_key_bytes, public_key_bytes), both raw 32-byte values."""
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_bytes = private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    public_bytes = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return private_bytes, public_bytes


def sign(private_key_bytes: bytes, message: bytes) -> bytes:
    private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    return private_key.sign(message)


def verify(public_key_bytes: bytes, message: bytes, signature: bytes) -> bool:
    public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
    try:
        public_key.verify(signature, message)
        return True
    except InvalidSignature:
        return False
