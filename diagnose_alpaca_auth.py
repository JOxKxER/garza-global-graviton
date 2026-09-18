#!/usr/bin/env python3
"""Diagnose Alpaca paper-account authentication with a raw HTTP request.

This intentionally uses HTTP Basic Auth because it is useful for testing the
reported failure mode. Alpaca's Trading API normally expects the API key ID
and secret in APCA-API-KEY-ID / APCA-API-SECRET-KEY headers; use the optional
--header-auth comparison to test that scheme in the same process.

Credentials are read from ALPACA_API_KEY and ALPACA_SECRET_KEY only. Never
commit them or place them directly in this file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Mapping

import requests
from requests.auth import HTTPBasicAuth

DEFAULT_ENDPOINT = "https://paper-api.alpaca.markets/v2/account"
_SENSITIVE_HEADER_PARTS = ("authorization", "api-key", "secret", "token", "cookie")


def _redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for name, value in headers.items():
        lowered = name.lower()
        redacted[name] = "<redacted>" if any(part in lowered for part in _SENSITIVE_HEADER_PARTS) else value
    return redacted


def _print_response(label: str, response: requests.Response) -> None:
    print(f"\n--- {label} ---")
    print(f"Status: {response.status_code} {response.reason}")
    print("Response headers:")
    print(json.dumps(_redact_headers(response.headers), indent=2, sort_keys=True))
    print("Response payload:")
    try:
        print(json.dumps(response.json(), indent=2, sort_keys=True))
    except ValueError:
        print(response.text[:4000])


def request_with_basic_auth(endpoint: str, api_key: str, secret_key: str, timeout: float) -> requests.Response:
    return requests.get(
        endpoint,
        auth=HTTPBasicAuth(api_key, secret_key),
        headers={"Accept": "application/json", "User-Agent": "alpaca-auth-diagnostic/1.0"},
        timeout=timeout,
    )


def request_with_api_headers(endpoint: str, api_key: str, secret_key: str, timeout: float) -> requests.Response:
    return requests.get(
        endpoint,
        headers={
            "Accept": "application/json",
            "User-Agent": "alpaca-auth-diagnostic/1.0",
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
        },
        timeout=timeout,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default=os.getenv("ALPACA_ACCOUNT_ENDPOINT", DEFAULT_ENDPOINT))
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument(
        "--header-auth",
        action="store_true",
        help="Also call the endpoint using Alpaca's documented API-key headers.",
    )
    args = parser.parse_args()

    api_key = os.getenv("ALPACA_API_KEY", "").strip()
    secret_key = os.getenv("ALPACA_SECRET_KEY", "").strip()
    if not api_key or not secret_key:
        print(
            "Missing ALPACA_API_KEY or ALPACA_SECRET_KEY. "
            "Set them in the process environment; do not put secrets in this script.",
            file=sys.stderr,
        )
        return 2

    print(f"Endpoint: {args.endpoint}")
    print(f"API key ID: {api_key[:4]}...{api_key[-4:]}")
    print("Secret key: <redacted>")
    print("Auth scheme: HTTP Basic Auth")

    try:
        response = request_with_basic_auth(args.endpoint, api_key, secret_key, args.timeout)
        _print_response("HTTP Basic Auth", response)
        exit_code = 0 if response.ok else 1

        if args.header_auth:
            header_response = request_with_api_headers(args.endpoint, api_key, secret_key, args.timeout)
            _print_response("Alpaca API-key headers", header_response)
            exit_code = 0 if header_response.ok else exit_code
        return exit_code
    except requests.RequestException as exc:
        print(f"Request failed before receiving an HTTP response: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
