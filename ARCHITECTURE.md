# Global Graviton Gauntlet (#GGG) — Architecture Specification

**Garza Global Graviton LLC · v1.4.5 · Sovereign Edge Daemon & Local Data Vault**

---

## 1. Design Doctrine

The #GGG node is not a server. It is a **Synthetic Data Center**: a single piece
of local, air-gapped hardware organized like a living organism rather than a
rack of anonymous services. Every subsystem answers to four invariants:

| Invariant | Enforcement |
|---|---|
| **Local-first** | All state lives on the operator's machine; the daemon is fully functional with the WAN interface physically removed. |
| **Zero telemetry** | No analytics, beacons, or phone-home code paths exist in the codebase. Auditable, not promised. |
| **Loopback containment** | All inter-process and AI inference traffic traverses loopback or operator-designated LAN addresses only. |
| **Absolute data ownership** | Vault contents belong to the hardware operator. The vendor has no access mechanism — by construction. |

---

## 2. System Topology

```
┌────────────────────────────────────────────────────────────────┐
│                     OPERATOR HARDWARE (AIR-GAP)                 │
│                                                                │
│   ┌──────────────┐    loopback    ┌─────────────────────────┐  │
│   │  index.html  │◄──────────────►│  Loopback API Gateway    │  │
│   │  C2 Monitor  │  GET /api/tags │  (status, read-only)     │  │
│   └──────────────┘                └───────────┬─────────────┘  │
│                                               │                │
│                              ┌────────────────▼─────────────┐  │
│                              │   Ollama Daemon (11434)      │  │
│                              │   qwen2.5-coder / llama3.x   │  │
│                              └────────────────┬─────────────┘  │
│                                               │                │
│   ┌───────────────────────────────────────────▼─────────────┐  │
│   │              PI ENGINE (pressure-relief scheduler)       │  │
│   │   metabolic pacer · admission control · thermal valve    │  │
│   └───────────────┬───────────────────────┬─────────────────┘  │
│                   │                       │                    │
│   ┌───────────────▼────────┐   ┌──────────▼─────────────────┐  │
│   │  LUNGS — zero-copy     │   │  LOCAL DATA VAULT          │  │
│   │  ring buffer (I/O)     │   │  SQLite ledgers · sealed   │  │
│   └───────────────┬────────┘   │  snapshots · localStorage  │  │
│                   │            │  browser vault             │  │
│   ┌───────────────▼────────┐   └────────────────────────────┘  │
│   │  LIVER — vectorized    │                                   │
│   │  memory sanitation     │                                   │
│   └───────────────┬────────┘                                   │
│                   │                                            │
│   ┌───────────────▼────────┐                                   │
│   │  IMMUNE — zero-trust   │                                   │
│   │  signature scanner     │                                   │
│   └────────────────────────┘                                   │
└────────────────────────────────────────────────────────────────┘
```

---

## 3. Loopback API Gateway

The gateway is the node's only network-facing surface, and it is deliberately
minimal.

- **Binding.** The reference configuration targets the operator's LAN adapter
  (`http://192.168.1.236:11434`) or loopback (`http://localhost:11434`). The
  companion web console additionally enforces a **client-side allowlist**:
  `localhost`, `127.0.0.1`, and `[::1]` — any other hostname is rejected in the
  browser *before a socket is opened* (see `isLocalOnlyUrl()` in
  [index.html](index.html)).
- **Read-only status surface.** The C2 monitor issues `GET /` and
  `GET /api/tags` sweeps with a 3-second `AbortController` timeout, reporting
  link state, round-trip latency, and installed model inventory. **No prompts,
  payloads, or state are transmitted** — the status plane is strictly one-way
  read.
- **Inference plane (optional, user-initiated).** When the operator enables
  chat/app-builder surfaces, requests go to `/api/chat` (Ollama native) or
  `/v1/chat/completions` (OpenAI-compatible) — always over the same
  loopback/LAN boundary, never to a remote host.
- **CORS contract.** The daemon must be launched with `OLLAMA_ORIGINS="*"` (or
  the specific console origin) for browser clients. The desktop shell's content
  security policy independently constrains `connect-src` to
  `http://localhost:11434` and `http://127.0.0.1:11434`
  (see [src-tauri/tauri.conf.json](src-tauri/tauri.conf.json)) — meaning the
  packaged binary **structurally cannot egress to the cloud**, even if
  instructed to.

## 4. Local-First Data Vault

The vault is layered, and every layer is operator-owned:

| Layer | Technology | Purpose |
|---|---|---|
| **Session vault** | Browser `localStorage` (`ggg_*` keys) | Chat history, sealed enterprise inquiries, archive packages, rolling continuous-backup snapshot |
| **Ledger store** | SQLite (`cluster_ledger.db`, `vault.db`, `vault_storage.db`) | Node-local append-only ledgers and vault metadata |
| **Snapshot engine** | `snapshot_engine.py` / `archive_snapshot.py` | Sealed, timestamped recovery points with manifest verification |
| **Seal manifest** | `SEAL_MANIFEST.json` + `manifest_verifier.py` | Cryptographic integrity attestation for releases and backups |

Archival is format-flexible (Structured JSON / Markdown / RFC-4180 CSV) and
always ends in two destinations: the local vault **and** a user-downloaded file.
There is no third destination.

## 5. Zero Telemetry Posture

Zero telemetry is an architectural property, not a policy statement:

1. **No code paths.** There is no analytics SDK, beacon, crash reporter, or
   usage-ping module anywhere in the source tree.
2. **Verifiable on the wire.** The C2 monitor itself can be used to confirm the
   node originates no outbound flows beyond operator-designated LAN targets.
3. **CSP enforcement.** The Tauri shell's `default-src 'self'` + loopback-only
   `connect-src` makes exfiltration attempts fail at the webview layer.
4. **License enforcement.** The license (Section 4.2) prohibits redistributing
   modified builds that inject tracking without explicit end-user consent.

## 6. The Daemon as a "Pi Engine" — Mathematical Pressure Relief

Local AI runtimes fail in a characteristic way: they accept work faster than
silicon can retire it, so queues deepen, KV caches balloon, and the process
dies under its own backlog. The daemon's answer is the **pi engine** — a
metabolic pressure-relief valve named for its governing constant.

### 6.1 The control loop

Every workload (inference request, I/O burst, sanitation sweep) must pass an
admission gate paced by a microsecond-precision heartbeat. The gate tracks the
node's instantaneous **pressure** — the ratio of queued demand to sustainable
throughput — and relieves it the way a valve relieves a vessel.

The engine draws its name from the isoperimetric principle: a circle encloses
maximum area for a given perimeter. The daemon treats the node's sustainable
capacity $C$ as that perimeter and continuously re-shapes the admitted workload
$W(t)$ so that it occupies the *largest useful area* — maximum useful work —
without ever exceeding the boundary:

$$ \max \; \text{Utility}(W) \quad \text{subject to} \quad \oint W(t)\,dt \;\le\; 2\pi r \cdot C $$

In practice the controller integrates queued pressure $P(t)$ over the pacing
interval and admits work only while the integral stays inside the circle:

$$ P(t) = \frac{Q_{\text{queued}}(t)}{Q_{\text{sustainable}}}, \qquad
   \text{admit} \iff \int_{t-\tau}^{t} P(u)\,du < \pi $$

When the integral approaches $\pi$, the valve closes — new work is deferred,
the **liver** preemptively scrubs stale allocations, and the **lungs** slow
their intake — until the pressure integral relaxes. Like $\pi$ itself, the
threshold never terminates and never repeats into instability: the system
converges to its sustainable rhythm instead of oscillating.

### 6.2 Why this matters for local AI

- **Cold-start amortization.** Model weights load once per boot
  (`keep_alive`), not once per request; the pacer spreads the cost.
- **Backpressure without loss.** Deferred work is queued in the vault, not
  dropped — the operator sees pending pressure on the C2 dashboard instead of
  a hung process.
- **Hardware-shaped.** Because pacing is measured against *this* node's
  observed throughput (not a spec sheet), the same daemon breathes correctly on
  a Raspberry Pi and on a multi-GPU workstation.

### 6.3 Measured operating envelope

From the node's published physics benchmarks (see the on-page table in
[index.html](index.html)):

| Operation | Local cost |
|---|---|
| Zero-copy buffer read/write | ~0.1 – 2 µs |
| Heartbeat pacer cycle | ~50 – 200 µs |
| Vectorized memory scrub | ~10 – 500 µs |
| Zero-trust signature scan | ~50 µs – 1 ms |

Three orders of magnitude below any network hop — which is the entire point:
**control decisions happen at hardware speed because the controller is on the
hardware.**

## 7. Desktop Shell (Tauri)

The native wrapper ([src-tauri/](src-tauri/)) packages the console as `.exe` /
`.app`:

- Pings `http://localhost:11434/api/tags` (2s timeout) **before revealing the
  window**; injects a recovery banner with exact `ollama serve` / `ollama pull`
  commands if the daemon is down.
- System-tray hooks: Show / Recheck Ollama / Quit; close-to-tray lifecycle.
- Release profile: LTO + strip + `codegen-units = 1` for a minimal binary.

Build procedure: [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md).

## 8. Trust & Verification

Every claim in this document is checkable:

- Audit the source (license Section 2.2 grants it).
- Verify release integrity against `SEAL_MANIFEST.json`.
- Watch the wire — the zero-telemetry posture survives a packet capture.

*Sovereign. Air-gapped. Locally owned.*
