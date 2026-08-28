import copy
import secrets

import pytest

from cnc_attestation import signing
from cnc_attestation.controller_quote import (
    CncAttestationBundle,
    build_bundle,
    build_quote,
    validate_firmware_hash,
    validate_isolation_flags,
    verify_merkle_root_matches_manifest,
    verify_quote_signature,
    verify_quoted_data_binding,
)
from cnc_attestation.gcode_merkle import GCodeManifestBuilder
from cnc_attestation.verify_cnc_client import verify


@pytest.fixture
def sealed_manifest():
    builder = GCodeManifestBuilder(commitment_id="commit-test", job_salt=secrets.token_bytes(16))
    builder.record_job_start("pytest-job", total_lines=2)
    builder.record_line_executed(0, "G1 X10 Y0")
    builder.record_line_executed(1, "G1 X10 Y10")
    builder.record_job_end(2, True)
    return builder.seal()


@pytest.fixture
def controller_keys():
    return signing.generate_keypair()


@pytest.fixture
def nonce():
    return secrets.token_bytes(16)


@pytest.fixture
def isolation_flags():
    return {
        "wifi_radio_enabled": False,
        "bluetooth_enabled": False,
        "ethernet_link_detected": False,
        "usb_network_gadget_enabled": False,
        "cellular_modem_present": False,
    }


@pytest.fixture
def bundle(sealed_manifest, controller_keys, nonce, isolation_flags):
    controller_priv, controller_pub = controller_keys
    quote = build_quote(
        controller_priv, controller_pub, "a" * 64, isolation_flags, sealed_manifest.merkle_root, nonce
    )
    return build_bundle(sealed_manifest, quote)


def test_valid_bundle_passes(bundle, controller_keys, nonce):
    _, controller_pub = controller_keys
    result = verify(bundle, controller_pub, nonce, {"a" * 64})
    assert result["passed"], result["reasons"]


def test_tampered_event_breaks_merkle_check(bundle, controller_keys, nonce):
    _, controller_pub = controller_keys
    tampered = CncAttestationBundle.from_dict(copy.deepcopy(bundle.to_dict()))
    tampered.manifest.events[1].payload["line_number"] = 999
    result = verify(tampered, controller_pub, nonce, {"a" * 64})
    assert not result["passed"]
    assert result["checks"]["merkle_root_matches_manifest"] is False


def test_wifi_radio_enabled_fails_isolation_check(sealed_manifest, controller_keys, nonce, isolation_flags):
    controller_priv, controller_pub = controller_keys
    leaky_flags = dict(isolation_flags)
    leaky_flags["wifi_radio_enabled"] = True
    quote = build_quote(
        controller_priv, controller_pub, "a" * 64, leaky_flags, sealed_manifest.merkle_root, nonce
    )
    leaky_bundle = build_bundle(sealed_manifest, quote)
    result = verify(leaky_bundle, controller_pub, nonce, {"a" * 64})
    assert not result["passed"]
    assert result["checks"]["serial_isolation_confirmed"] is False


def test_missing_isolation_flag_is_treated_as_violation(
    sealed_manifest, controller_keys, nonce, isolation_flags
):
    controller_priv, controller_pub = controller_keys
    incomplete_flags = dict(isolation_flags)
    del incomplete_flags["bluetooth_enabled"]
    quote = build_quote(
        controller_priv, controller_pub, "a" * 64, incomplete_flags, sealed_manifest.merkle_root, nonce
    )
    result = verify(build_bundle(sealed_manifest, quote), controller_pub, nonce, {"a" * 64})
    assert not result["passed"]
    assert any("missing isolation flag" in r for r in result["reasons"])


def test_untrusted_firmware_hash_fails(bundle, controller_keys, nonce):
    _, controller_pub = controller_keys
    result = verify(bundle, controller_pub, nonce, {"c" * 64})
    assert not result["passed"]
    assert result["checks"]["firmware_hash_trusted"] is False


def test_no_firmware_allowlist_is_treated_as_unverified_not_a_pass(bundle, controller_keys, nonce):
    _, controller_pub = controller_keys
    result = verify(bundle, controller_pub, nonce, None)
    assert not result["passed"]
    assert result["checks"]["firmware_hash_trusted"] is False


def test_wrong_controller_pubkey_fails_signature_check(bundle, nonce):
    _, wrong_pub = signing.generate_keypair()
    result = verify(bundle, wrong_pub, nonce, {"a" * 64})
    assert not result["passed"]
    assert result["checks"]["quote_signature_valid"] is False


def test_wrong_nonce_fails_replay_check(bundle, controller_keys):
    _, controller_pub = controller_keys
    stale_nonce = secrets.token_bytes(16)
    result = verify(bundle, controller_pub, stale_nonce, {"a" * 64})
    assert not result["passed"]
    assert result["checks"]["nonce_matches_challenge"] is False


def test_helper_functions_agree_with_verify(bundle, controller_keys):
    _, controller_pub = controller_keys
    assert verify_merkle_root_matches_manifest(bundle)
    assert verify_quote_signature(bundle.quote, controller_pub)
    assert verify_quoted_data_binding(bundle.quote)
    assert validate_isolation_flags(bundle.quote) == []
    assert validate_firmware_hash(bundle.quote, {"a" * 64})
    assert validate_firmware_hash(bundle.quote, None) is True  # explicitly "skipped", see docstring
