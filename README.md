# Garza Global Graviton LLC — Sovereign Platform

**Garza Global Graviton LLC** builds sovereign, 100% air-gapped edge
computing systems — hardware and software that run entirely on local
infrastructure, with zero mandatory network dependency, zero cloud
telemetry, and zero vendor-side visibility into your data.

## v1.4.0 — Mobile-Responsive Web Hub

The node's local web hub ([`index.html`](index.html)) is now fully
mobile-responsive as of **v1.4.0**: brand bars, the hardware plaque, the
physics benchmark table, and the local Ollama bridge all reflow cleanly on
phones and tablets (screens under 768px), with buttons, inputs, and panels
expanding to full width for comfortable touch interaction, and the physics
benchmark table gaining smooth horizontal scrolling instead of a broken
layout.

### 100% Air-Gapped Sovereign Edge

Every node runs as a **Synthetic Data Center**: a single piece of local,
air-gapped hardware organized like a living organism, paced and defended by
cooperating biological daemons that never touch the network:

- **Metabolic Heart** — paces admission and pulses the node's cadence at
  microsecond precision.
- **Liver** — scrubs stale memory in-place with vectorized zeroization,
  never leaving residue.
- **Lungs** — inhale and exhale data through a zero-copy ring buffer,
  moving bytes without ever duplicating them.
- **Immune System** — a zero-trust scanner that quarantines and
  neutralizes any byte pattern it does not recognize.

Because every buffer is a single preallocated `memoryview` over a `numpy`
array, data moves through the organism without a single extra copy, and
because the node is air-gapped, every daemon above runs at local hardware
speed, not network speed.

- **Local-only by construction.** The Ollama bridge only accepts
  `localhost` / `127.0.0.1` / `[::1]` endpoints; remote hosts are rejected
  before any request is ever sent, keeping the bridge 100% offline by
  construction.
- **Sovereign data ownership.** Nothing leaves the device unless you
  explicitly choose to send it — there is no cloud dependency in the
  critical path.

### Download the release bundle

Grab the latest packaged sovereign app from the GitHub Releases page:

```
https://github.com/JOxKxER/garza-global-graviton/releases/latest
```

Or click **Download Sovereign App** directly from the top of the local web
hub ([`index.html`](index.html)).

### Connect your local Ollama instance

1. Install and start [Ollama](https://ollama.com) on the same machine (or
   another host reachable at `localhost`/loopback).
2. Pull a model, e.g. `ollama pull llama3.2:3b`.
3. Open `index.html` in a browser and, in the **Local Ollama Bridge**
   panel, confirm the endpoint (default `http://localhost:11434`) and model
   name, then click **Check Status**.
4. Once the badge shows **ONLINE**, use the **Live Local Benchmark** panel
   or the chat row to send prompts — everything runs locally, offline.

---

## Running the daemon binary — Windows SmartScreen

The released `ggg-daemon.exe` is self-signed (no commercial code-signing
certificate), so Windows SmartScreen will show **"Windows protected your
PC"** on first launch. This is expected for unsigned local binaries — it is
a reputation warning, not a detection.

**To run it:**

1. On the SmartScreen dialog, click **"More info"**.
2. Click **"Run anyway"** — the choice is remembered for that file.

**Verify authenticity before running** (recommended): every release ships a
`SHA256SUMS.txt` alongside the binary. Compare the hash:

```powershell
Get-FileHash .\ggg-daemon_v1.4.5_windows.zip -Algorithm SHA256
# Then compare against the matching line in SHA256SUMS.txt
```

If the hash matches the published manifest, the binary is exactly what this
repository built. If it does not match, do not run it.

---

## Use your local Ollama as the model provider in VS Code

Keep your editor 100% local by pointing a local-model extension at the same
Ollama daemon (`http://localhost:11434`). Add to your VS Code `settings.json`
(`Ctrl+Shift+P` → *Preferences: Open User Settings (JSON)*):

```json
{
  "continue.server": {
    "port": 11434
  },
  "continue.models": [
    {
      "title": "GGG Local Qwen",
      "provider": "ollama",
      "model": "qwen2.5-coder:latest",
      "apiBase": "http://localhost:11434"
    }
  ],
  "ollama.baseUrl": "http://localhost:11434",
  "localai.model.basePath": "http://localhost:11434"
}
```

- **Continue.dev** (`Continue.continue`): the `continue.models` entry selects
  your local `qwen2.5-coder` as the chat/edit model. See
  [.continue/config.json](.continue/config.json) for this repo's ready-made
  Continue configuration.
- **Ollama extensions** (e.g. `Ollama.ollama`): `ollama.baseUrl` redirects
  all model calls to loopback.
- **GitHub Copilot** does not support custom/local model providers — use
  Continue or an Ollama extension for fully offline AI assistance.

---

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

## Background system maintenance (`GGGMachineBoost` Windows service)

[`machine_boost_supervisor.py`](machine_boost_supervisor.py) runs this
machine's legitimate maintenance/health daemons on a schedule, with automatic
restart for the long-running ones. [`machine_boost_service.py`](machine_boost_service.py)
wraps it as a native Windows service (via `pywin32`) so it starts at **boot**,
not just at user logon.

| Daemon | Mode | Interval |
|---|---|---|
| `watchdog_daemon.py` | one-shot, re-run | every 5 minutes |
| `system_watchdog.py` | one-shot, re-run | every 5 minutes |
| `snapshot_daemon.py` | one-shot, re-run | every 60 minutes |
| `mesh_ping_daemon.py` | one-shot, re-run | every 1 minute |
| `health_monitor.py` | persistent (self-looping) | started once, auto-restarted if it exits |

**Deliberately excluded:** `traffic_daemon.py` and `live_cluster_daemon.py`.
Both generate fake synthetic "client orders" tagged with real defense
contractor names (Lockheed, DARPA, Raytheon, General Dynamics, Northrop)
against a local API with a hardcoded key -- not a maintenance function, and
not something that should run unattended at every machine startup fabricating
usage data attributed to real companies.

**Environment hardening applied to every managed child process:**

| Variable | Why it's required |
|---|---|
| `PYTHONIOENCODING=utf-8` | Several daemons print emoji; without this they crash with `UnicodeEncodeError` the moment they run without a real console (exactly the situation under a Windows service). |
| `PYTHONUTF8=1` | Belt-and-suspenders UTF-8 mode for the child interpreter. |
| `PYTHONUNBUFFERED=1` | Piped stdout is fully block-buffered by default (not line-buffered); without this, `health_monitor.py`'s output can sit invisible in the child's buffer indefinitely instead of streaming to the log. |

The supervisor's own `subprocess.run`/`Popen` calls also pass
`encoding="utf-8"` explicitly -- `text=True` alone still decodes captured
output using the OS locale (cp1252 on this machine) regardless of what the
child's own encoding is set to, which silently reintroduces the same crash
one layer up if omitted.

All output is logged to `logs/machine_boost_supervisor.log` (git-ignored;
it's runtime state, not source).

### Installing the service (requires an elevated/Administrator shell)

```powershell
pip install -r requirements.txt   # installs pywin32 among the rest
python machine_boost_service.py install
python machine_boost_service.py start
```

Check on it later:

```powershell
Get-Service GGGMachineBoost
Get-Content logs\machine_boost_supervisor.log -Tail 50 -Wait
```

Stop/remove it:

```powershell
python machine_boost_service.py stop
python machine_boost_service.py remove
```

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
