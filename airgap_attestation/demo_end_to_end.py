"""End-to-end smoke test for the zero-network-leakage attestation pipeline.
Run directly: python demo_end_to_end.py
"""

import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from airgap_attestation import signing
from airgap_attestation.attestation import ReferenceSoftwareAttestor
from airgap_attestation.audit_manifest import AuditManifestBuilder, LocalReferenceMonitor
from airgap_attestation.proof_bundle import build_bundle, load_bundle, save_bundle
from airgap_attestation.verify_client import verify_bundle


def main() -> None:
    # --- Vendor side: one-time platform keypair (published/pinned out of band) ---
    platform_private_key, platform_public_key = signing.generate_keypair()

    # --- Client side: issues a fresh nonce per submission to prevent replay ---
    client_nonce = secrets.token_bytes(16)

    # --- Vendor side: run the job inside the (simulated) air-gapped enclave ---
    builder = AuditManifestBuilder(commitment_id="commit-demo-001", network_monitor=LocalReferenceMonitor())
    builder.record_process_start(job_label="acme-corp-sample-run-7")
    builder.record_syscall_category_counts(
        {"file_io": 4213, "process_exec": 12, "socket": 0, "connect": 0, "sendto": 0, "bind": 0}
    )
    builder.record_network_snapshot()
    builder.record_process_end(exit_code=0)
    manifest = builder.seal()

    attestor = ReferenceSoftwareAttestor()  # swap for Tpm2ToolsAttestor in production
    bundle = build_bundle(
        manifest=manifest,
        attestor=attestor,
        platform_private_key=platform_private_key,
        platform_public_key=platform_public_key,
        nonce=client_nonce,
    )

    bundle_path = os.path.join(os.path.dirname(__file__), "demo_bundle.json")
    save_bundle(bundle, bundle_path)
    print(f"Wrote attestation bundle to {bundle_path}")

    # --- Client side: fully offline verification of the delivered bundle ---
    reloaded = load_bundle(bundle_path)
    result = verify_bundle(
        reloaded,
        trusted_platform_pubkey=platform_public_key,
        expected_nonce=client_nonce,
        trusted_ak_pubkeys=[attestor.ak_public_key],
        reject_software_reference_quotes=False,  # demo only; True in production
    )

    print("\nVerification checks:")
    for name, ok in result.checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if result.reasons:
        print("\nReasons for any failures:")
        for reason in result.reasons:
            print(f"  - {reason}")
    print(f"\nOVERALL: {'PASSED' if result.passed else 'FAILED'}")


if __name__ == "__main__":
    main()
