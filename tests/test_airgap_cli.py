import json
import secrets

import pytest

from airgap_attestation import signing
from airgap_attestation.attestation import ReferenceSoftwareAttestor
from airgap_attestation.audit_manifest import AuditManifestBuilder, LocalReferenceMonitor
from airgap_attestation.cli.verify_cli import main
from airgap_attestation.proof_bundle import build_bundle, save_bundle


@pytest.fixture
def bundle_file(tmp_path):
    builder = AuditManifestBuilder(
        commitment_id="commit-cli-test", network_monitor=LocalReferenceMonitor()
    )
    builder.record_process_start(job_label="cli-test")
    builder.record_process_end(exit_code=0)
    manifest = builder.seal()

    platform_private, platform_public = signing.generate_keypair()
    attestor = ReferenceSoftwareAttestor()
    nonce = secrets.token_bytes(16)
    generated_bundle = build_bundle(
        manifest=manifest,
        attestor=attestor,
        platform_private_key=platform_private,
        platform_public_key=platform_public,
        nonce=nonce,
    )

    path = tmp_path / "AttestationBundle.json"
    save_bundle(generated_bundle, str(path))
    return path, platform_public, nonce, attestor.ak_public_key


def test_cli_exits_zero_on_valid_bundle(bundle_file, capsys):
    path, platform_public, nonce, ak_pubkey = bundle_file
    exit_code = main(
        [
            "--bundle",
            str(path),
            "--platform-pubkey",
            platform_public.hex(),
            "--nonce",
            nonce.hex(),
            "--ak-pubkey",
            ak_pubkey.hex(),
            "--allow-software-reference",
        ]
    )
    assert exit_code == 0
    assert "RESULT: PASSED" in capsys.readouterr().out


def test_cli_exits_one_on_wrong_pubkey(bundle_file, capsys):
    path, _, nonce, ak_pubkey = bundle_file
    _, wrong_pubkey = signing.generate_keypair()
    exit_code = main(
        [
            "--bundle",
            str(path),
            "--platform-pubkey",
            wrong_pubkey.hex(),
            "--nonce",
            nonce.hex(),
            "--ak-pubkey",
            ak_pubkey.hex(),
            "--allow-software-reference",
        ]
    )
    assert exit_code == 1
    assert "RESULT: FAILED" in capsys.readouterr().out


def test_cli_exits_two_on_missing_file(tmp_path, capsys):
    missing_path = tmp_path / "does-not-exist.json"
    exit_code = main(["--bundle", str(missing_path), "--platform-pubkey", "ab" * 32])
    assert exit_code == 2


def test_cli_json_output_mode(bundle_file, capsys):
    path, platform_public, nonce, ak_pubkey = bundle_file
    exit_code = main(
        [
            "--bundle",
            str(path),
            "--platform-pubkey",
            platform_public.hex(),
            "--nonce",
            nonce.hex(),
            "--ak-pubkey",
            ak_pubkey.hex(),
            "--allow-software-reference",
            "--json",
        ]
    )
    assert exit_code == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["passed"] is True


def test_cli_reads_hex_key_from_file(bundle_file, tmp_path, capsys):
    path, platform_public, nonce, ak_pubkey = bundle_file
    key_file = tmp_path / "platform_pub.hex"
    key_file.write_text(platform_public.hex())

    exit_code = main(
        [
            "--bundle",
            str(path),
            "--platform-pubkey",
            str(key_file),
            "--nonce",
            nonce.hex(),
            "--ak-pubkey",
            ak_pubkey.hex(),
            "--allow-software-reference",
        ]
    )
    assert exit_code == 0
