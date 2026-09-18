"""Read-only Kalshi market-data connector for the local analytics engine."""

from __future__ import annotations

import base64
import asyncio
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from sports_analytics_engine import OddsRecord, PoliteLimiter, utc_now


DEFAULT_KALSHI_URL = "https://api.elections.kalshi.com/trade-api/v2/markets"


class KalshiMarketConnector:
    """Fetch open Kalshi markets without accessing trading operations."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        limiter: PoliteLimiter,
        url: str = DEFAULT_KALSHI_URL,
        max_retries: int = 3,
        limit: int = 100,
    ) -> None:
        self.client = client
        self.limiter = limiter
        self.url = url
        self.max_retries = max_retries
        self.limit = limit
        self.api_key_id = os.environ.get("KALSHI_API_KEY_ID", "").strip()
        self.private_key_path = os.environ.get("KALSHI_PRIVATE_KEY_PATH", "").strip()

    def _private_key(self) -> Any:
        if not self.api_key_id or not self.private_key_path:
            raise RuntimeError(
                "KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY_PATH must be configured"
            )
        key_bytes = Path(self.private_key_path).read_bytes()
        return serialization.load_pem_private_key(key_bytes, password=None)

    def _headers(self, method: str, path: str) -> dict[str, str]:
        timestamp = str(int(time.time() * 1000))
        message = f"{timestamp}{method.upper()}{path}".encode("utf-8")
        signature = self._private_key().sign(
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
            hashes.SHA256(),
        )
        return {
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode("ascii"),
            "Accept": "application/json",
        }

    async def fetch(self) -> list[OddsRecord]:
        last_error: Exception | None = None
        parsed_url = httpx.URL(self.url)
        for attempt in range(self.max_retries + 1):
            await self.limiter.wait()
            try:
                response = await self.client.get(
                    self.url,
                    headers=self._headers("GET", parsed_url.raw_path.decode("ascii")),
                    params={"status": "open", "limit": str(self.limit)},
                )
                response.raise_for_status()
                return self._normalize(response.json())
            except (
                httpx.HTTPError,
                OSError,
                ValueError,
                TypeError,
                KeyError,
            ) as error:
                last_error = error
                if attempt >= self.max_retries:
                    break
                await asyncio.sleep(min(60, 2**attempt))
        raise RuntimeError("Kalshi market request failed") from last_error

    def _normalize(self, payload: Any) -> list[OddsRecord]:
        markets = payload.get("markets", []) if isinstance(payload, dict) else []
        records: list[OddsRecord] = []
        observed_at = utc_now()
        for market in markets:
            if not isinstance(market, dict):
                continue
            ticker = str(market.get("ticker", "")).strip()
            title = str(market.get("title", ticker)).strip()
            if not ticker or not title:
                continue
            category = str(market.get("category", "kalshi"))
            close_time = market.get("close_time", market.get("expiration_time", ""))
            if isinstance(close_time, (int, float)):
                close_time = datetime.fromtimestamp(
                    close_time, timezone.utc
                ).isoformat().replace("+00:00", "Z")
            for outcome, cents in (
                ("Yes", market.get("yes_bid", market.get("yes_ask"))),
                ("No", market.get("no_bid", market.get("no_ask"))),
            ):
                try:
                    probability = float(cents) / 100
                    if not 0 < probability < 1:
                        continue
                    price = (
                        round(-100 * probability / (1 - probability))
                        if probability > 0.5
                        else round((1 / probability - 1) * 100)
                    )
                except (TypeError, ValueError, ZeroDivisionError):
                    continue
                records.append(OddsRecord(
                    event_id=ticker,
                    sport="prediction-market",
                    league=category,
                    home_team="Kalshi",
                    away_team=title,
                    commence_time=str(close_time),
                    bookmaker="Kalshi",
                    market="prediction",
                    outcome=outcome,
                    price_american=price,
                    point=None,
                    observed_at=observed_at,
                    source="kalshi-public-markets",
                    category="kalshi",
                ))
        return records
