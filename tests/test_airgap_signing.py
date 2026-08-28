import pytest

from airgap_attestation import signing


def test_generate_keypair_lengths():
    private_key, public_key = signing.generate_keypair()
    assert len(private_key) == 32
    assert len(public_key) == 32


def test_sign_and_verify_round_trip():
    private_key, public_key = signing.generate_keypair()
    message = b"execution-manifest-digest"
    signature = signing.sign(private_key, message)
    assert signing.verify(public_key, message, signature)


def test_verify_rejects_tampered_message():
    private_key, public_key = signing.generate_keypair()
    signature = signing.sign(private_key, b"original")
    assert not signing.verify(public_key, b"tampered", signature)


def test_verify_rejects_wrong_key():
    private_key, _ = signing.generate_keypair()
    _, other_public_key = signing.generate_keypair()
    message = b"payload"
    signature = signing.sign(private_key, message)
    assert not signing.verify(other_public_key, message, signature)


def test_verify_rejects_corrupted_signature():
    private_key, public_key = signing.generate_keypair()
    message = b"payload"
    signature = bytearray(signing.sign(private_key, message))
    signature[0] ^= 0xFF
    assert not signing.verify(public_key, message, bytes(signature))
