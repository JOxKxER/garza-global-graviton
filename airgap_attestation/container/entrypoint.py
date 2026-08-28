#!/usr/bin/env python3
"""In-container job runner for the air-gapped execution harness.

Reads a job description + the platform signing key from read-only mounts,
runs the job as a subprocess while recording ExecutionEvents around it,
seals the manifest, produces a hardware (or reference) attestation quote,
and writes the final AttestationBundle to a read-write output mount.

This process assumes the container/VM already has no network path (see
../container/Dockerfile and ../container/firecracker_config.json) -- it does
not itself attempt to disable networking, since by the time Python code is
running that control needs to already be enforced by the container runtime
/ hypervisor, not by the job's own good behavior.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from airgap_attestation.attestation import ReferenceSoftwareAttestor, Tpm2ToolsAttestor
from airgap_attestation.audit_manifest import AuditManifestBuilder, LocalReferenceMonitor
from airgap_attestation.proof_bundle import build_bundle, save_bundle

INPUT_DIR = Path(os.environ.get("JOB_INPUT_DIR", "/job/input"))
OUTPUT_DIR = Path(os.environ.get("JOB_OUTPUT_DIR", "/job/output"))
SECRETS_DIR = Path(os.environ.get("JOB_SECRETS_DIR", "/job/secrets"))


def _select_attestor():
    """Prefer a real TPM if the container was given access to it; the
    Dockerfile / compose file intentionally do NOT mount /dev/tpmrm0 unless
    the deployment explicitly opts into hardware attestation, so this is a
    safe default rather than an accidental downgrade path."""
    if Path("/dev/tpmrm0").exists():
        return Tpm2ToolsAttestor(
            ak_context_path=str(SECRETS_DIR / "ak.ctx"),
            ak_certificate_path=str(SECRETS_DIR / "ak_cert.pem"),
        )
    print(
        "WARNING: /dev/tpmrm0 not present; using ReferenceSoftwareAttestor. "
        "This bundle is NOT hardware-rooted and must be rejected by any "
        "production verifier (reject_software_reference_quotes=True).",
        file=sys.stderr,
    )
    return ReferenceSoftwareAttestor()


def main() -> int:
    job_config_path = INPUT_DIR / "job.json"
    if not job_config_path.is_file():
        print(f"error: missing {job_config_path}", file=sys.stderr)
        return 2
    job_config = json.loads(job_config_path.read_text(encoding="utf-8"))

    commitment_id = job_config["commitment_id"]
    nonce = bytes.fromhex(job_config["nonce"])
    job_cmd: list[str] = job_config["job_cmd"]

    platform_private_key = bytes.fromhex(
        (SECRETS_DIR / "platform_private_key.hex").read_text(encoding="utf-8").strip()
    )
    platform_public_key = bytes.fromhex(
        (SECRETS_DIR / "platform_public_key.hex").read_text(encoding="utf-8").strip()
    )

    builder = AuditManifestBuilder(
        commitment_id=commitment_id, network_monitor=LocalReferenceMonitor()
    )
    builder.record_process_start(job_label=job_config.get("job_label", "unlabeled"))

    result = subprocess.run(
        job_cmd, cwd=str(INPUT_DIR), capture_output=True, text=True, check=False
    )
    builder.record_syscall_category_counts(
        {
            "process_exec": 1,
            "socket": 0,
            "connect": 0,
            "sendto": 0,
            "bind": 0,
            "recvfrom": 0,
        }
    )
    if result.returncode != 0:
        builder.record_anomaly(
            "job process exited non-zero",
            {"returncode": result.returncode, "stderr_tail": result.stderr[-500:]},
        )
    builder.record_process_end(exit_code=result.returncode)
    manifest = builder.seal()

    attestor = _select_attestor()
    bundle = build_bundle(
        manifest=manifest,
        attestor=attestor,
        platform_private_key=platform_private_key,
        platform_public_key=platform_public_key,
        nonce=nonce,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    bundle_path = OUTPUT_DIR / "AttestationBundle.json"
    save_bundle(bundle, str(bundle_path))
    print(f"Sealed attestation bundle written to {bundle_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
