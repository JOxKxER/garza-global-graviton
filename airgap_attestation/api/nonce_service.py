"""Backend API for the commit-reveal submission flow.

Public-facing endpoints (client-callable):
  POST /v1/submissions             -> issue a single-use nonce for a blinded sample
  GET  /v1/submissions/{id}         -> poll submission status
  GET  /v1/submissions/{id}/bundle  -> download the finished AttestationBundle

Internal-only endpoint (called by the air-gapped runner's export step, via a
separate management network / sneakernet upload station -- never reachable
from the same network segment as a client):
  POST /v1/internal/submissions/{id}/bundle

Run locally:
    uvicorn airgap_attestation.api.nonce_service:app --host 0.0.0.0 --port 8443
"""

from __future__ import annotations

import json
import os
import re
import time
from collections import defaultdict

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from .store import SubmissionStore

_HEX64 = re.compile(r"^[0-9a-f]{64}$")  # sha256 digest, and also Ed25519 raw pubkey length

INTERNAL_INGEST_KEY_ENV = "AIRGAP_INTERNAL_INGEST_KEY"

# In-memory rate limiter, per-process only -- swap for Redis (or another
# shared store) once this runs behind more than one worker/instance, since
# each process would otherwise track its own independent request counts.
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 10
_client_request_log: dict[str, list[float]] = defaultdict(list)

app = FastAPI(title="Air-Gap Attestation Submission Service", version="1.0")
_store = SubmissionStore(db_path=os.environ.get("AIRGAP_SUBMISSIONS_DB", "submissions.db"))


@app.middleware("http")
async def security_and_rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    # Unauthenticated nonce issuance is the endpoint most worth throttling:
    # it's the one an attacker could hammer to exhaust the submissions DB or
    # probe for timing side-channels without needing any credentials.
    if request.method == "POST" and request.url.path == "/v1/submissions":
        history = [t for t in _client_request_log[client_ip] if now - t < RATE_LIMIT_WINDOW_SECONDS]
        if len(history) >= RATE_LIMIT_MAX_REQUESTS:
            return Response(status_code=429, content="Rate limit exceeded. Please try again later.")
        history.append(now)
        _client_request_log[client_ip] = history

    response: Response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


class SubmissionRequest(BaseModel):
    sample_commitment_hash: str = Field(..., description="hex sha256(sample || salt)")
    client_pubkey: str = Field(..., description="hex Ed25519 public key")


class SubmissionResponse(BaseModel):
    commitment_id: str
    nonce: str
    nonce_expires_at: str


class StatusResponse(BaseModel):
    commitment_id: str
    status: str
    created_at: str
    nonce_expires_at: str
    bundle_available: bool


class IngestBundleRequest(BaseModel):
    bundle: dict


def _require_internal_key(x_internal_ingest_key: str = Header(default="")) -> None:
    expected = os.environ.get(INTERNAL_INGEST_KEY_ENV)
    if not expected:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"{INTERNAL_INGEST_KEY_ENV} is not configured on this server",
        )
    if not x_internal_ingest_key or x_internal_ingest_key != expected:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "invalid internal ingest key")


@app.post("/v1/submissions", response_model=SubmissionResponse)
def create_submission(req: SubmissionRequest) -> SubmissionResponse:
    if not _HEX64.match(req.sample_commitment_hash.lower()):
        raise HTTPException(422, "sample_commitment_hash must be 64 hex characters (sha256)")
    if not _HEX64.match(req.client_pubkey.lower()):
        raise HTTPException(422, "client_pubkey must be 64 hex characters (Ed25519 raw key)")

    record = _store.create_submission(
        sample_commitment_hash=req.sample_commitment_hash.lower(),
        client_pubkey=req.client_pubkey.lower(),
    )
    return SubmissionResponse(
        commitment_id=record.commitment_id,
        nonce=record.nonce,
        nonce_expires_at=record.nonce_expires_at,
    )


@app.get("/v1/submissions/{commitment_id}", response_model=StatusResponse)
def get_status(commitment_id: str) -> StatusResponse:
    record = _store.get(commitment_id)
    if record is None:
        raise HTTPException(404, "unknown commitment_id")
    return StatusResponse(
        commitment_id=record.commitment_id,
        status=record.status,
        created_at=record.created_at,
        nonce_expires_at=record.nonce_expires_at,
        bundle_available=record.bundle_json is not None,
    )


@app.get("/v1/submissions/{commitment_id}/bundle")
def get_bundle(commitment_id: str) -> dict:
    record = _store.get(commitment_id)
    if record is None:
        raise HTTPException(404, "unknown commitment_id")
    if record.bundle_json is None:
        raise HTTPException(409, f"bundle not ready yet (status={record.status})")
    return json.loads(record.bundle_json)


@app.post("/v1/internal/submissions/{commitment_id}/bundle")
def ingest_bundle(
    commitment_id: str,
    req: IngestBundleRequest,
    _: None = Depends(_require_internal_key),
) -> dict:
    record = _store.get(commitment_id)
    if record is None:
        raise HTTPException(404, "unknown commitment_id")
    if _store.nonce_is_expired(record):
        _store.mark_rejected(commitment_id, "nonce expired before bundle ingest")
        raise HTTPException(410, "nonce expired; client must resubmit for a fresh challenge")

    quote_nonce = (
        req.bundle.get("tpm_quote", {}).get("nonce", "") if isinstance(req.bundle, dict) else ""
    )
    if quote_nonce != record.nonce:
        _store.mark_rejected(commitment_id, "bundle nonce does not match issued nonce")
        raise HTTPException(
            409, "bundle's tpm_quote.nonce does not match the nonce issued for this submission"
        )

    accepted = _store.attach_bundle(
        commitment_id, json.dumps(req.bundle), quote_nonce=quote_nonce
    )
    if not accepted:
        raise HTTPException(
            409, "nonce already consumed (possible replay) or commitment_id unknown"
        )
    return {"commitment_id": commitment_id, "status": "READY"}


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}
