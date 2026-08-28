# Client Onboarding: Zero-Network-Leakage Attestation

This is the step-by-step guide for a prospective enterprise client to submit
a blinded test sample, receive a cryptographically sealed
`AttestationBundle.json`, and verify it **entirely offline** -- no vendor
source code, SDK, or network access is required to check the result.

Everything below maps directly to real modules in this repository:
`airgap_attestation/api/nonce_service.py` (backend), `airgap_attestation/cli/verify_cli.py`
(your verifier), and `airgap_attestation/schemas.py` (the data you'll see).

---

## 0. Before you start

You need:
- Python 3.9+ on your own machine (the verification step never touches the
  vendor's network or systems).
- The vendor's **pinned Ed25519 platform public key** and **AK (Attestation
  Key) public key**, obtained once out of band (e.g. printed in your master
  services agreement) -- never accept these values over the same channel as
  a bundle itself.
- This repository's `airgap_attestation/` package available locally (clone
  or copy it; it has no vendor-proprietary code in it).

---

## 1. Generate your commitment locally

Never send your raw test sample to the vendor's intake API. Hash it with a
random salt first:

```python
import hashlib, secrets

sample_bytes = open("my_test_input.bin", "rb").read()
salt = secrets.token_bytes(16)
commitment_hash = hashlib.sha256(sample_bytes + salt).hexdigest()

# Keep `salt` secret and safe -- you'll need it later to prove which sample
# was actually tested (the "reveal" half of commit-reveal).
```

Also generate a client keypair (used only to identify your submission, not
to encrypt anything here):

```python
from airgap_attestation import signing
client_private_key, client_public_key = signing.generate_keypair()
```

## 2. Request a challenge nonce from the backend

```bash
curl -X POST https://<vendor-api-host>/v1/submissions \
  -H "Content-Type: application/json" \
  -d '{
        "sample_commitment_hash": "<commitment_hash from step 1>",
        "client_pubkey": "<client_public_key.hex() from step 1>"
      }'
```

Response:

```json
{
  "commitment_id": "03c467cf-4220-4b3c-8953-2002b94b5ead",
  "nonce": "b0df2134cf0bc8cacb4105e08cfa23ac",
  "nonce_expires_at": "2026-08-28T07:00:33Z"
}
```

**Save `commitment_id` and `nonce`.** The nonce is single-use and time-boxed
(default 15 minutes) -- if it expires before the vendor's run completes,
you'll need to request a fresh one; an expired nonce can never be reused
(see `SubmissionStore.attach_bundle` / `nonce_is_expired`).

## 3. Deliver the encrypted sample to the vendor (out of band)

Send the vendor:
- The encrypted sample payload (encrypt it yourself with a key you control).
- Your `commitment_id`.

Send the decryption key/salt through a **separate** channel from the
encrypted payload itself (e.g. a phone call, a sealed physical drive, a
different secure messenger) -- never bundle the key with the ciphertext.
This is what prevents the vendor from silently substituting a different
sample: the commitment hash you already published cryptographically binds
them to the exact bytes you intended.

## 4. Poll for status

```bash
curl https://<vendor-api-host>/v1/submissions/<commitment_id>
```

```json
{
  "commitment_id": "03c467cf-4220-4b3c-8953-2002b94b5ead",
  "status": "PENDING",
  "created_at": "2026-08-28T06:45:33Z",
  "nonce_expires_at": "2026-08-28T07:00:33Z",
  "bundle_available": false
}
```

`status` becomes `"READY"` once the vendor's air-gapped run completes and
its `AttestationBundle.json` has been ingested.

## 5. Download the attestation bundle

```bash
curl https://<vendor-api-host>/v1/submissions/<commitment_id>/bundle \
  -o AttestationBundle.json
```

This file contains the sealed execution log (`manifest`), the hardware
quote (`tpm_quote`), and the vendor's signature (`platform_signature`) --
see `airgap_attestation/schemas.py::AttestationBundle` for the exact shape.
Nothing in it is proprietary; it's safe to archive for your own compliance
records.

## 6. Verify it yourself, fully offline

```bash
python airgap_attestation/cli/verify_cli.py \
  --bundle AttestationBundle.json \
  --platform-pubkey <vendor's pinned Ed25519 public key, hex or a file path> \
  --nonce <the nonce you received in step 2> \
  --ak-pubkey <vendor's pinned Attestation Key public key, hex or a file path>
```

Example output:

```
Bundle:   AttestationBundle.json
Bundle ID: 86dcb811-bf0c-4d60-bb90-1294684b18e5
Manifest:  afec4a8d-d2bb-4804-b80b-437ef330ba78 (6 events)

  [PASS] platform_pubkey_matches_pinned
  [PASS] platform_signature_valid
  [PASS] merkle_root_matches_events
  [PASS] quote_binds_current_merkle_root
  [PASS] nonce_matches_challenge
  [PASS] quote_is_hardware_rooted
  [PASS] ak_certificate_chains_to_trust_root
  [PASS] bundle_within_validity_window
  [PASS] zero_network_activity_observed

RESULT: PASSED
```

The command's exit code is machine-readable too: `0` = passed, `1` = failed
(a real check failed -- do not proceed with purchase), `2` = usage/file
error (fix your command line, not a trust decision). Add `--json` for a
CI-friendly machine-readable report.

### Reading a FAILED result

Every failed check names exactly what went wrong (see the `reasons` list in
`--json` output or the "Details" section of the text output) -- for example
a Merkle root mismatch means the event log was altered after sealing, and a
nonce mismatch means you may be looking at a replayed, stale attestation.
Do not accept a bundle with any failing check.

## 7. Confirm the reveal (optional but recommended)

Ask the vendor to confirm the `salt` from step 1 out of band, then recompute
`sha256(sample_bytes + salt)` yourself and check it equals the
`sample_commitment_hash` you originally submitted. This closes the loop:
the Merkle-sealed manifest proves *what happened during execution*, and the
reveal proves *it happened to your exact sample*, not a substitute.

---

## Summary of trust anchors you must pin ahead of time

| Anchor | Source | Used for |
|---|---|---|
| Platform Ed25519 public key | Vendor's MSA / compliance packet | `--platform-pubkey` |
| Attestation Key (AK) public key/cert | Vendor's MSA / compliance packet | `--ak-pubkey` |
| Nonce | Your own `/v1/submissions` response | `--nonce` (anti-replay) |

If a bundle ever arrives with a different platform key than the one you
pinned, **stop** -- do not add the new key as "probably fine." Contact the
vendor through an independent channel to confirm before proceeding.
