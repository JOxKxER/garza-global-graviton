"""Small RapidAPI-compatible public-page extraction service."""

from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, Header, HTTPException

app = FastAPI(title="Data Extraction Micro-Service", version="1.0.0")
RAPID_PROXY_SECRET = os.environ.get("RAPIDAPI_PROXY_SECRET", "dev-secret")
MAX_RESPONSE_BYTES = 2_000_000


def _validate_public_url(target_url: str) -> None:
    parsed = urlparse(target_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=400, detail="target_url must be an HTTP or HTTPS URL.")

    try:
        addresses = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise HTTPException(status_code=400, detail="target_url host could not be resolved.") from exc

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise HTTPException(status_code=400, detail="Private or reserved target hosts are not allowed.")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "active"}


@app.get("/extract-data")
async def extract_data(
    target_url: str,
    x_rapidapi_proxy_secret: str | None = Header(default=None),
) -> dict[str, object]:
    if os.environ.get("ENFORCE_RAPIDAPI", "false").lower() == "true":
        if not x_rapidapi_proxy_secret or x_rapidapi_proxy_secret != RAPID_PROXY_SECRET:
            raise HTTPException(status_code=401, detail="Unauthorized RapidAPI proxy request.")

    _validate_public_url(target_url)

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            response = await client.get(
                target_url,
                headers={"User-Agent": "DataExtractionMicroService/1.0"},
            )
        response.raise_for_status()
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise HTTPException(status_code=413, detail="Target response is too large to process.")
    except HTTPException:
        raise
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Target returned HTTP {exc.response.status_code}.",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Target request failed.") from exc

    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else "No Title"
    headings = [heading.get_text(" ", strip=True) for heading in soup.find_all(["h1", "h2"])[:10]]

    return {
        "status": "success",
        "url": target_url,
        "page_title": title,
        "key_headings": headings,
    }
