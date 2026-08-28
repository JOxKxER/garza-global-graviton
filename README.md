# Air-Gap Zero-Network-Leakage Attestation Platform

Cryptographic proof, for prospective enterprise buyers, that a sensitive
manufacturing/data pipeline ran in a strictly air-gapped, tamper-evident
environment -- verifiable entirely offline, without ever seeing the vendor's
proprietary pipeline source.

All of this lives under [`airgap_attestation/`](airgap_attestation/).

> **Honesty note:** no software system can produce an unconditional
> *mathematical* proof of "zero network leakage" from a black box. What this
> platform delivers is a layered, tamper-evident, independently falsifiable
> evidence chain (hardware-rooted measurement + a cryptographically sealed
> execution log + dual signatures) where any single point of compromise is
> detectable. See [`airgap_attestation/CLIENT_ONBOARDING.md`](airgap_attestation/CLIENT_ONBOARDING.md)
> for what a buyer should actually conclude from a passing/failing result.

---

## Architecture

```
CLIENT                          AIR-GAPPED EXECUTION ENCLAVE                CLIENT
  |  1. commit-reveal blind         |  a. TPM/enclave measured boot            |
  |     (sha256(sample||salt))      |  b. NIC disabled at hardware level       |
  |--- POST /v1/submissions ------->|  c. job runs; AuditManifestBuilder       |
  |<-- {commitment_id, nonce} ------|     records PROCESS_START/END,          |
  |                                 |     NET_IFACE_SNAPSHOT, syscall counts   |
  |  2. deliver encrypted sample    |  d. events sealed into a Merkle tree     |
  |     (out-of-band, key sent      |  e. TPM/enclave QUOTE(nonce||root)       |
  |      via a SEPARATE channel)    |  f. platform Ed25519 signature over      |
  |                                 |     (root, quote, validity window)       |
  |  3. poll GET /v1/submissions/{id}                                          |
  |  4. GET /v1/submissions/{id}/bundle -> AttestationBundle.json ------------>|
  |                                                                            |
  |                                              5. verify_cli.py, fully      |
  |                                                 offline: Merkle root,      |
  |                                                 TPM quote, platform sig,   |
  |                                                 nonce freshness, zero-     |
  |                                                 network invariant          |
  |                                                 -> PASS / FAIL            |
```

Full protocol writeup (data schemas, hashing/signing details, edge cases):
see the architecture discussion in project history, or read the code directly
-- every design decision is documented as a comment at its point of use:
[`merkle.py`](airgap_attestation/merkle.py), [`schemas.py`](airgap_attestation/schemas.py),
[`verify_client.py`](airgap_attestation/verify_client.py).

## Repository layout

```
airgap_attestation/
  merkle.py             Domain-separated Merkle tree (leaf/node hash separation,
                         no odd-node duplication -- avoids classic forgery bugs)
  schemas.py             Wire-format dataclasses (SubmissionCommitment, ExecutionEvent,
                         AuditManifest, TpmQuoteEvidence, AttestationBundle, ...)
  signing.py              Ed25519 keygen/sign/verify (platform transport-layer identity)
  attestation.py          HardwareAttestor interface: Tpm2ToolsAttestor (real TPM 2.0,
                         via tpm2-tools) + ReferenceSoftwareAttestor (dev/test only,
                         explicitly rejected by production verification)
  audit_manifest.py       AuditManifestBuilder + NetworkActivityMonitor (pluggable;
                         LocalReferenceMonitor ships as a portable fallback)
  proof_bundle.py         Assembles/signs/saves/loads the final AttestationBundle
  verify_client.py        The entire client-side verifier -- no vendor source needed
  demo_end_to_end.py       Runnable proof-of-concept: build -> sign -> verify
  api/
    store.py              SQLite-backed, single-use nonce/commitment store (atomic
                         UPDATE ... WHERE guard -- no TOCTOU replay window)
    nonce_service.py       FastAPI backend: submission intake, status, bundle
                         download, internal ingest, rate limiting, security headers
  cli/
    verify_cli.py          Buyer-facing CLI wrapper around verify_client.py
  container/
    Dockerfile             Hardened image: distroless nonroot final stage
    docker-compose.yml (repo-relative: airgap_attestation/docker-compose.yml)
                         network_mode: none, read_only, cap_drop ALL, seccomp
    seccomp-hardened.json  Kernel-level deny-list for network syscalls
    firecracker_config.json  Stronger alternative: no NIC device exists at all
    entrypoint.py           In-container job runner
    deployment_runbook.ps1  Step-by-step build/run/ingest/verify commands
  CLIENT_ONBOARDING.md     Buyer-facing, step-by-step usage guide

tests/
  test_airgap_merkle.py, test_airgap_signing.py, test_airgap_pipeline.py,
  test_airgap_api.py, test_airgap_cli.py     (60 tests, ~84% coverage of the package)

render.yaml                  Render deployment blueprint for nonce_service:app
.github/workflows/ci.yml     GitHub Actions: pytest + coverage on push/PR
init_repo.ps1                 Release packaging script (see below)
```

---

## Quickstart (local development)

```powershell
# From the repository root:
python -m pip install -r requirements.txt
python -m pip install pytest-cov   # only needed for local coverage reports

# Run the standalone end-to-end demo (build -> sign -> verify a sample bundle):
python airgap_attestation\demo_end_to_end.py

# Run the backend API locally:
$env:AIRGAP_INTERNAL_INGEST_KEY = "dev-only-key"
uvicorn airgap_attestation.api.nonce_service:app --reload --port 8443
```

## Running the test suite

```powershell
python -m pytest tests/ --cov=airgap_attestation --cov-report=term-missing
```

Expect `60 passed`, ~84% coverage. The one large coverage gap
(`attestation.py`, ~61%) is `Tpm2ToolsAttestor` -- the real-hardware TPM 2.0
code path, which is untestable without physical TPM hardware and is not
mocked out just to inflate the number.

## Container hardening

See [`airgap_attestation/container/`](airgap_attestation/container/) and its
`deployment_runbook.ps1`. Summary of the layered controls (any one being
misconfigured must not compromise the others):

| Control | Where | What it guarantees |
|---|---|---|
| `network_mode: none` | `docker-compose.yml` | No network namespace peer at all |
| `network-interfaces: []` | `firecracker_config.json` | No NIC device exists for the guest (hypervisor-level, stronger than netns) |
| `seccomp-hardened.json` | `docker-compose.yml` | Kernel-level deny of every network syscall, defense in depth under `--network none` |
| `read_only` + `cap_drop: [ALL]` | `docker-compose.yml` | Immutable rootfs, no elevated capabilities |
| `distroless nonroot` base image | `Dockerfile` | No shell, no package manager, uid 65532 |

## Deploying the backend API

```bash
# Render (see render.yaml): create a Blueprint instance pointing at this repo.
# It provisions the web service + a 1GB persistent disk at /var/data for the
# SubmissionStore's SQLite file, and generates AIRGAP_INTERNAL_INGEST_KEY for you.
```

Endpoints exposed by `nonce_service.py` (see
[`CLIENT_ONBOARDING.md`](airgap_attestation/CLIENT_ONBOARDING.md) for full
request/response examples):

| Method | Path | Caller |
|---|---|---|
| `POST` | `/v1/submissions` | Client -- issue a single-use nonce |
| `GET` | `/v1/submissions/{id}` | Client -- poll status |
| `GET` | `/v1/submissions/{id}/bundle` | Client -- download the sealed bundle |
| `POST` | `/v1/internal/submissions/{id}/bundle` | Vendor's air-gapped runner export step only (key-protected) |
| `GET` | `/healthz` | Load balancer / uptime check |

## Enterprise client onboarding

Buyers should start at
[`airgap_attestation/CLIENT_ONBOARDING.md`](airgap_attestation/CLIENT_ONBOARDING.md),
which walks through: generating a commit-reveal hash, requesting a nonce,
delivering the sample out-of-band, polling for the bundle, and running

```bash
python airgap_attestation/cli/verify_cli.py \
  --bundle AttestationBundle.json \
  --platform-pubkey <pinned vendor key> \
  --nonce <the nonce you received> \
  --ak-pubkey <pinned vendor Attestation Key>
```

Exit code `0` = passed, `1` = a real check failed (do not proceed with
purchase), `2` = usage/file error.

## CI

[`ci.yml`](.github/workflows/ci.yml) runs on every push/PR to `main`: Python
3.11, installs `requirements.txt`, runs the full test suite with coverage,
and uploads the coverage report (`coverage.xml` + HTML) as a build artifact.

## Releasing

```powershell
.\init_repo.ps1                 # stage, commit, tag v1.0.0-release (no push)
.\init_repo.ps1 -Push           # also push the branch and tag to origin
```

This repository already has git history and an `origin` remote; the script
detects that and only adds a new commit + tag for this milestone -- it does
not reinitialize or rewrite existing history.
