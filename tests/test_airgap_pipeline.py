import copy
import secrets

import pytest

from airgap_attestation import signing
from airgap_attestation.attestation import ReferenceSoftwareAttestor
from airgap_attestation.audit_manifest import AuditManifestBuilder, LocalReferenceMonitor
from airgap_attestation.proof_bundle import build_bundle
from airgap_attestation.schemas import AttestationBundle
from airgap_attestation.verify_client import verify_bundle


@pytest.fixture
def sealed_manifest():
    builder = AuditManifestBuilder(
        commitment_id="commit-test-001", network_monitor=LocalReferenceMonitor()
    )
    builder.record_process_start(job_label="pytest-run")
    builder.record_syscall_category_counts(
        {"file_io": 42, "process_exec": 1, "socket": 0, "connect": 0, "sendto": 0, "bind": 0}
    )
    builder.record_process_end(exit_code=0)
    return builder.seal()


@pytest.fixture
def keys():
    platform_private, platform_public = signing.generate_keypair()
    return platform_private, platform_public


@pytest.fixture
def nonce():
    return secrets.token_bytes(16)


@pytest.fixture
def bundle(sealed_manifest, keys, nonce):
    platform_private, platform_public = keys
    attestor = ReferenceSoftwareAttestor()
    built = build_bundle(
        manifest=sealed_manifest,
        attestor=attestor,
        platform_private_key=platform_private,
        platform_public_key=platform_public,
        nonce=nonce,
    )
    return built, attestor


def test_valid_bundle_passes_verification(bundle, keys, nonce):
    built, attestor = bundle
    _, platform_public = keys
    result = verify_bundle(
        built,
        trusted_platform_pubkey=platform_public,
        expected_nonce=nonce,
        trusted_ak_pubkeys=[attestor.ak_public_key],
        reject_software_reference_quotes=False,
    )
    assert result.passed, result.reasons
    assert all(result.checks.values())


def test_software_reference_quote_rejected_by_default(bundle, keys, nonce):
    built, attestor = bundle
    _, platform_public = keys
    result = verify_bundle(
        built,
        trusted_platform_pubkey=platform_public,
        expected_nonce=nonce,
        trusted_ak_pubkeys=[attestor.ak_public_key],
        # reject_software_reference_quotes defaults to True
    )
    assert not result.passed
    assert result.checks["quote_is_hardware_rooted"] is False


def test_wrong_platform_pubkey_rejected(bundle, nonce):
    built, attestor = bundle
    _, wrong_public_key = signing.generate_keypair()
    result = verify_bundle(
        built,
        trusted_platform_pubkey=wrong_public_key,
        expected_nonce=nonce,
        trusted_ak_pubkeys=[attestor.ak_public_key],
        reject_software_reference_quotes=False,
    )
    assert not result.passed
    assert result.checks["platform_pubkey_matches_pinned"] is False
    assert result.checks["platform_signature_valid"] is False


def test_replay_with_wrong_nonce_rejected(bundle, keys):
    built, attestor = bundle
    _, platform_public = keys
    stale_nonce = secrets.token_bytes(16)
    result = verify_bundle(
        built,
        trusted_platform_pubkey=platform_public,
        expected_nonce=stale_nonce,
        trusted_ak_pubkeys=[attestor.ak_public_key],
        reject_software_reference_quotes=False,
    )
    assert not result.passed
    assert result.checks["nonce_matches_challenge"] is False


def test_tampered_event_payload_breaks_merkle_root_check(bundle, keys, nonce):
    built, attestor = bundle
    _, platform_public = keys

    tampered = AttestationBundle.from_dict(copy.deepcopy(built.to_dict()))
    for event in tampered.manifest.events:
        if event.payload.get("counts"):
            event.payload["counts"]["connect"] = 3
            break

    result = verify_bundle(
        tampered,
        trusted_platform_pubkey=platform_public,
        expected_nonce=nonce,
        trusted_ak_pubkeys=[attestor.ak_public_key],
        reject_software_reference_quotes=False,
    )
    assert not result.passed
    assert result.checks["merkle_root_matches_events"] is False
    assert result.checks["zero_network_activity_observed"] is False
    assert any("connect" in reason for reason in result.reasons)


def test_network_activity_in_manifest_is_detected():
    builder = AuditManifestBuilder(
        commitment_id="commit-with-network", network_monitor=LocalReferenceMonitor()
    )
    builder.record_process_start(job_label="leaky-job")
    builder.record_syscall_category_counts({"socket": 1, "connect": 1})
    builder.record_process_end(exit_code=0)
    manifest = builder.seal()

    platform_private, platform_public = signing.generate_keypair()
    attestor = ReferenceSoftwareAttestor()
    leaky_nonce = secrets.token_bytes(16)
    leaky_bundle = build_bundle(
        manifest=manifest,
        attestor=attestor,
        platform_private_key=platform_private,
        platform_public_key=platform_public,
        nonce=leaky_nonce,
    )

    result = verify_bundle(
        leaky_bundle,
        trusted_platform_pubkey=platform_public,
        expected_nonce=leaky_nonce,
        trusted_ak_pubkeys=[attestor.ak_public_key],
        reject_software_reference_quotes=False,
    )
    assert not result.passed
    assert result.checks["zero_network_activity_observed"] is False
