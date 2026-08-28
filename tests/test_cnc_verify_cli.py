import json
import secrets

import pytest

from cnc_attestation import signing
from cnc_attestation.controller_quote import build_bundle, build_quote, save_bundle
from cnc_attestation.gcode_merkle import GCodeManifestBuilder
from cnc_attestation.verify_cnc_client import main


@pytest.fixture
def bundle_file(tmp_path):
    builder = GCodeManifestBuilder(commitment_id="c1", job_salt=secrets.token_bytes(16))
    builder.record_job_start("cli-test", total_lines=1)
    builder.record_line_executed(0, "G1 X10 Y0")
    builder.record_job_end(1, True)
    manifest = builder.seal()

    controller_priv, controller_pub = signing.generate_keypair()
    nonce = secrets.token_bytes(16)
    firmware_hash = "d" * 64
    flags = {
        "wifi_radio_enabled": False,
        "bluetooth_enabled": False,
        "ethernet_link_detected": False,
        "usb_network_gadget_enabled": False,
        "cellular_modem_present": False,
    }
    quote = build_quote(controller_priv, controller_pub, firmware_hash, flags, manifest.merkle_root, nonce)
    bundle = build_bundle(manifest, quote)

    path = tmp_path / "CncAttestationBundle.json"
    save_bundle(bundle, str(path))
    return path, controller_pub, nonce, firmware_hash


def test_cli_exits_zero_on_valid_bundle(bundle_file, capsys):
    path, controller_pub, nonce, firmware_hash = bundle_file
    exit_code = main(
        [
            "--bundle",
            str(path),
            "--controller-pubkey",
            controller_pub.hex(),
            "--nonce",
            nonce.hex(),
            "--trusted-firmware-hash",
            firmware_hash,
        ]
    )
    assert exit_code == 0
    assert "RESULT: PASSED" in capsys.readouterr().out


def test_cli_exits_one_on_wrong_pubkey(bundle_file, capsys):
    path, _, nonce, firmware_hash = bundle_file
    _, wrong_pub = signing.generate_keypair()
    exit_code = main(
        [
            "--bundle",
            str(path),
            "--controller-pubkey",
            wrong_pub.hex(),
            "--nonce",
            nonce.hex(),
            "--trusted-firmware-hash",
            firmware_hash,
        ]
    )
    assert exit_code == 1
    assert "RESULT: FAILED" in capsys.readouterr().out


def test_cli_exits_two_on_missing_bundle_file(tmp_path):
    missing = tmp_path / "nope.json"
    exit_code = main(["--bundle", str(missing), "--controller-pubkey", "ab" * 32])
    assert exit_code == 2


def test_cli_json_output_mode(bundle_file, capsys):
    path, controller_pub, nonce, firmware_hash = bundle_file
    exit_code = main(
        [
            "--bundle",
            str(path),
            "--controller-pubkey",
            controller_pub.hex(),
            "--nonce",
            nonce.hex(),
            "--trusted-firmware-hash",
            firmware_hash,
            "--json",
        ]
    )
    assert exit_code == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["passed"] is True


def test_cli_reads_pubkey_from_file(bundle_file, tmp_path):
    path, controller_pub, nonce, firmware_hash = bundle_file
    key_file = tmp_path / "controller_pub.hex"
    key_file.write_text(controller_pub.hex())

    exit_code = main(
        [
            "--bundle",
            str(path),
            "--controller-pubkey",
            str(key_file),
            "--nonce",
            nonce.hex(),
            "--trusted-firmware-hash",
            firmware_hash,
        ]
    )
    assert exit_code == 0
