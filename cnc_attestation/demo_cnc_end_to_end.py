"""End-to-end smoke test for the CNC attestation pipeline.
Run directly: python demo_cnc_end_to_end.py
"""

import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cnc_attestation import signing
from cnc_attestation.controller_quote import build_bundle, build_quote, load_bundle, save_bundle
from cnc_attestation.gcode_merkle import (
    GCodeManifestBuilder,
    compute_gcode_commitment,
    verify_gcode_reveal,
)
from cnc_attestation.verify_cnc_client import verify

SAMPLE_GCODE = """G21 ; mm
G90 ; absolute
G0 Z5
G0 X0 Y0
M3 S12000
G1 X10 Y0 F800
G1 X10 Y10
G1 X0 Y10
G1 X0 Y0
M5
G0 Z25
""".strip()


def main() -> None:
    gcode_bytes = SAMPLE_GCODE.encode("utf-8")

    # --- Client: commit-reveal blinding ---
    client_salt = secrets.token_bytes(16)
    commitment_hash = compute_gcode_commitment(gcode_bytes, client_salt)
    commitment_id = "commit-cnc-demo-001"
    client_nonce = secrets.token_bytes(16)

    # --- Vendor: one-time controller (secure element) keypair ---
    controller_private_key, controller_public_key = signing.generate_keypair()
    firmware_hash = "a" * 64  # stand-in for sha256(firmware_image)

    # --- Isolated controller: run the job, recording events ---
    job_salt = secrets.token_bytes(16)  # per-job, distinct from the client's commitment salt
    builder = GCodeManifestBuilder(commitment_id=commitment_id, job_salt=job_salt)
    lines = SAMPLE_GCODE.splitlines()
    builder.record_job_start(job_label="acme-bracket-rev3", total_lines=len(lines))
    for i, line in enumerate(lines):
        builder.record_line_executed(line_number=i, gcode_line=line)
        if line.startswith("M3"):
            builder.record_spindle_state(rpm=12000, enabled=True)
        if line.startswith("M5"):
            builder.record_spindle_state(rpm=0, enabled=False)
    builder.record_job_end(lines_executed=len(lines), completed=True)
    manifest = builder.seal()

    isolation_flags = {
        "wifi_radio_enabled": False,
        "bluetooth_enabled": False,
        "ethernet_link_detected": False,
        "usb_network_gadget_enabled": False,
        "cellular_modem_present": False,
    }
    quote = build_quote(
        controller_private_key=controller_private_key,
        controller_public_key=controller_public_key,
        firmware_hash=firmware_hash,
        serial_isolation_flags=isolation_flags,
        merkle_root_hex=manifest.merkle_root,
        nonce=client_nonce,
    )
    bundle = build_bundle(manifest=manifest, quote=quote)

    bundle_path = os.path.join(os.path.dirname(__file__), "demo_cnc_bundle.json")
    save_bundle(bundle, bundle_path)
    print(f"Wrote CNC attestation bundle to {bundle_path}")

    # --- Client: offline verification ---
    reloaded = load_bundle(bundle_path)
    result = verify(
        reloaded,
        trusted_controller_pubkey=controller_public_key,
        expected_nonce=client_nonce,
        trusted_firmware_hashes={firmware_hash},
    )

    print("\nVerification checks:")
    for name, ok in result["checks"].items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if result["reasons"]:
        print("\nReasons for any failures:")
        for reason in result["reasons"]:
            print(f"  - {reason}")
    print(f"\nOVERALL: {'PASSED' if result['passed'] else 'FAILED'}")

    # --- Client: reveal check (confirms the exact G-code that was committed
    #     to before the job is the same G-code that was actually run) ---
    reveal_ok = verify_gcode_reveal(gcode_bytes, client_salt, commitment_hash)
    print(f"Commit-reveal check: {'OK' if reveal_ok else 'FAILED'}")


if __name__ == "__main__":
    main()
