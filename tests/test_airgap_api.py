import hashlib
import os
import secrets

import pytest

os.environ.setdefault("AIRGAP_SUBMISSIONS_DB", ":memory:")
os.environ.setdefault("AIRGAP_INTERNAL_INGEST_KEY", "test-ingest-key")

from fastapi.testclient import TestClient

from airgap_attestation import signing
from airgap_attestation.attestation import ReferenceSoftwareAttestor
from airgap_attestation.audit_manifest import AuditManifestBuilder, LocalReferenceMonitor
from airgap_attestation.proof_bundle import build_bundle


@pytest.fixture
def api_module(monkeypatch):
    """Re-import the service module per-test with a fresh in-memory DB so
    tests don't share submission/rate-limit state with each other."""
    monkeypatch.setenv("AIRGAP_SUBMISSIONS_DB", ":memory:")
    monkeypatch.setenv("AIRGAP_INTERNAL_INGEST_KEY", "test-ingest-key")
    import importlib

    from airgap_attestation.api import nonce_service

    importlib.reload(nonce_service)
    yield nonce_service
    nonce_service._store.close()


@pytest.fixture
def client(api_module):
    return TestClient(api_module.app)


def _new_commitment():
    _, client_pub = signing.generate_keypair()
    sample_hash = hashlib.sha256(secrets.token_bytes(16)).hexdigest()
    return sample_hash, client_pub.hex()


def test_create_submission_returns_nonce(client):
    sample_hash, client_pub_hex = _new_commitment()
    resp = client.post(
        "/v1/submissions",
        json={"sample_commitment_hash": sample_hash, "client_pubkey": client_pub_hex},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "commitment_id" in body
    assert len(bytes.fromhex(body["nonce"])) == 16


def test_create_submission_rejects_malformed_hash(client):
    resp = client.post(
        "/v1/submissions",
        json={"sample_commitment_hash": "not-hex", "client_pubkey": "ab" * 32},
    )
    assert resp.status_code == 422


def test_status_unknown_commitment_returns_404(client):
    resp = client.get("/v1/submissions/does-not-exist")
    assert resp.status_code == 404


def test_full_ingest_and_download_flow(client):
    sample_hash, client_pub_hex = _new_commitment()
    create_resp = client.post(
        "/v1/submissions",
        json={"sample_commitment_hash": sample_hash, "client_pubkey": client_pub_hex},
    )
    commitment_id = create_resp.json()["commitment_id"]
    nonce_hex = create_resp.json()["nonce"]

    platform_private, platform_public = signing.generate_keypair()
    builder = AuditManifestBuilder(
        commitment_id=commitment_id, network_monitor=LocalReferenceMonitor()
    )
    builder.record_process_start(job_label="api-test")
    builder.record_process_end(exit_code=0)
    manifest = builder.seal()

    attestor = ReferenceSoftwareAttestor()
    generated_bundle = build_bundle(
        manifest=manifest,
        attestor=attestor,
        platform_private_key=platform_private,
        platform_public_key=platform_public,
        nonce=bytes.fromhex(nonce_hex),
    )

    ingest_resp = client.post(
        f"/v1/internal/submissions/{commitment_id}/bundle",
        json={"bundle": generated_bundle.to_dict()},
        headers={"X-Internal-Ingest-Key": "test-ingest-key"},
    )
    assert ingest_resp.status_code == 200

    download_resp = client.get(f"/v1/submissions/{commitment_id}/bundle")
    assert download_resp.status_code == 200
    assert download_resp.json()["bundle_id"] == generated_bundle.bundle_id


def test_ingest_replay_is_rejected(client):
    sample_hash, client_pub_hex = _new_commitment()
    create_resp = client.post(
        "/v1/submissions",
        json={"sample_commitment_hash": sample_hash, "client_pubkey": client_pub_hex},
    )
    commitment_id = create_resp.json()["commitment_id"]
    nonce_hex = create_resp.json()["nonce"]

    platform_private, platform_public = signing.generate_keypair()
    builder = AuditManifestBuilder(
        commitment_id=commitment_id, network_monitor=LocalReferenceMonitor()
    )
    builder.record_process_start(job_label="replay-test")
    builder.record_process_end(exit_code=0)
    manifest = builder.seal()
    attestor = ReferenceSoftwareAttestor()
    generated_bundle = build_bundle(
        manifest=manifest,
        attestor=attestor,
        platform_private_key=platform_private,
        platform_public_key=platform_public,
        nonce=bytes.fromhex(nonce_hex),
    )

    headers = {"X-Internal-Ingest-Key": "test-ingest-key"}
    first = client.post(
        f"/v1/internal/submissions/{commitment_id}/bundle",
        json={"bundle": generated_bundle.to_dict()},
        headers=headers,
    )
    assert first.status_code == 200

    replay = client.post(
        f"/v1/internal/submissions/{commitment_id}/bundle",
        json={"bundle": generated_bundle.to_dict()},
        headers=headers,
    )
    assert replay.status_code == 409


def test_ingest_wrong_key_is_forbidden(client):
    sample_hash, client_pub_hex = _new_commitment()
    create_resp = client.post(
        "/v1/submissions",
        json={"sample_commitment_hash": sample_hash, "client_pubkey": client_pub_hex},
    )
    commitment_id = create_resp.json()["commitment_id"]

    resp = client.post(
        f"/v1/internal/submissions/{commitment_id}/bundle",
        json={"bundle": {}},
        headers={"X-Internal-Ingest-Key": "wrong-key"},
    )
    assert resp.status_code == 403


def test_security_headers_present_on_every_response(client):
    resp = client.get("/healthz")
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("strict-transport-security") == "max-age=31536000; includeSubDomains"
    assert resp.headers.get("content-security-policy") == "default-src 'self'"


def test_rate_limit_triggers_after_threshold(client):
    responses = []
    for _ in range(11):
        sample_hash, client_pub_hex = _new_commitment()
        responses.append(
            client.post(
                "/v1/submissions",
                json={"sample_commitment_hash": sample_hash, "client_pubkey": client_pub_hex},
            )
        )
    assert [r.status_code for r in responses[:10]] == [200] * 10
    assert responses[10].status_code == 429
