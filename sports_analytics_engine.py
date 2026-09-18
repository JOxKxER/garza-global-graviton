"""Informational sports odds aggregation and analysis engine.

This module is intentionally analysis-only. It never places bets, opens accounts,
handles funds, or communicates with sportsbook transaction endpoints. Configure
public odds APIs or public JSON feeds that you are permitted to access.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import random
import sqlite3
import time
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import httpx
import numpy as np
import pandas as pd

LOGGER = logging.getLogger("sports_analytics")
ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / "sports_analytics.db"


@dataclass(frozen=True)
class OddsRecord:
    event_id: str
    sport: str
    league: str
    home_team: str
    away_team: str
    commence_time: str
    bookmaker: str
    market: str
    outcome: str
    price_american: int
    point: float | None
    observed_at: str
    source: str
    category: str = "sportsbook"

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(
            asdict(self), sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class OddsConnectorConfig:
    name: str
    url: str
    sport: str = "basketball_nba"
    headers: dict[str, str] | None = None
    params: dict[str, str] | None = None
    provider: str = "odds"


class OddsConnector(Protocol):
    async def fetch(self) -> list[OddsRecord]:
        ...


class PoliteLimiter:
    def __init__(self, requests_per_second: float) -> None:
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        self.interval = 1.0 / requests_per_second
        self.lock = asyncio.Lock()
        self.next_request = 0.0

    async def wait(self) -> None:
        async with self.lock:
            now = asyncio.get_running_loop().time()
            delay = max(0.0, self.next_request - now)
            self.next_request = max(now, self.next_request) + self.interval
        if delay:
            await asyncio.sleep(delay + random.uniform(0, self.interval * 0.2))


class JsonOddsConnector:
    """Connector for The Odds API-compatible or configured public JSON feeds."""

    def __init__(
        self,
        config: OddsConnectorConfig,
        client: httpx.AsyncClient,
        limiter: PoliteLimiter,
        max_retries: int = 3,
    ) -> None:
        self.config = config
        self.client = client
        self.limiter = limiter
        self.max_retries = max_retries

    async def fetch(self) -> list[OddsRecord]:
        payload = await self.fetch_json()
        return self._normalize(payload)

    async def fetch_json(self) -> Any:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            await self.limiter.wait()
            try:
                response = await self.client.get(
                    self.config.url,
                    headers=self.config.headers or {},
                    params=self.config.params or {},
                )
                if response.status_code in {408, 425, 429, 500, 502, 503, 504}:
                    response.raise_for_status()
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError, TypeError, KeyError) as error:
                last_error = error
                if attempt >= self.max_retries:
                    break
                delay = min(60.0, 2**attempt + random.uniform(0, 0.5))
                LOGGER.warning("%s failed; retrying in %.1fs: %s", self.config.name, delay, error)
                await asyncio.sleep(delay)
        raise RuntimeError(f"connector failed: {self.config.name}") from last_error

    async def fetch_text(self) -> str:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            await self.limiter.wait()
            try:
                response = await self.client.get(
                    self.config.url,
                    headers=self.config.headers or {},
                    params=self.config.params or {},
                )
                response.raise_for_status()
                return response.text
            except httpx.HTTPError as error:
                last_error = error
                if attempt >= self.max_retries:
                    break
                await asyncio.sleep(min(60, 2**attempt))
        raise RuntimeError(f"connector failed: {self.config.name}") from last_error

    def _normalize(self, payload: Any) -> list[OddsRecord]:
        if self.config.provider == "polymarket":
            return self._normalize_polymarket(payload)
        events = payload.get("data", payload) if isinstance(payload, dict) else payload
        if not isinstance(events, list):
            raise ValueError("odds response must be a list or contain a data list")
        observed_at = utc_now()
        records: list[OddsRecord] = []
        for event in events:
            if not isinstance(event, dict):
                continue
            event_id = str(event.get("id", "")).strip()
            home = str(event.get("home_team", "")).strip()
            away = str(event.get("away_team", "")).strip()
            if not event_id or not home or not away:
                continue
            sport = str(event.get("sport_key", self.config.sport))
            league = str(event.get("sport_title", sport))
            commence = str(event.get("commence_time", ""))
            bookmakers = event.get("bookmakers", [])
            for bookmaker in bookmakers:
                bookmaker_name = str(bookmaker.get("title", bookmaker.get("key", "unknown")))
                for market in bookmaker.get("markets", []):
                    market_key = str(market.get("key", "unknown"))
                    for outcome in market.get("outcomes", []):
                        try:
                            price = int(outcome["price"])
                        except (KeyError, TypeError, ValueError):
                            continue
                        point = outcome.get("point")
                        records.append(OddsRecord(
                            event_id=event_id,
                            sport=sport,
                            league=league,
                            home_team=home,
                            away_team=away,
                            commence_time=commence,
                            bookmaker=bookmaker_name,
                            market=market_key,
                            outcome=str(outcome.get("name", "")),
                            price_american=price,
                            point=float(point) if point is not None else None,
                            observed_at=observed_at,
                            source=self.config.name,
                            category="sportsbook",
                        ))
        return records


    def _normalize_polymarket(self, payload: Any) -> list[OddsRecord]:
        """Normalize public Polymarket-style market objects into odds rows."""
        markets = payload.get("data", payload) if isinstance(payload, dict) else payload
        if not isinstance(markets, list):
            raise ValueError("Polymarket response must be a list or contain data")
        observed_at = utc_now()
        records: list[OddsRecord] = []
        for market in markets:
            if not isinstance(market, dict):
                continue
            market_id = str(market.get("id", market.get("conditionId", ""))).strip()
            question = str(market.get("question", market.get("title", ""))).strip()
            if not market_id or not question:
                continue
            outcomes = market.get("outcomes", [])
            prices = market.get("outcomePrices", [])
            if isinstance(outcomes, str):
                outcomes = json.loads(outcomes)
            if isinstance(prices, str):
                prices = json.loads(prices)
            if not isinstance(outcomes, list) or not isinstance(prices, list):
                continue
            event = market.get("event", {})
            category = str(
                market.get("category")
                or (event.get("category") if isinstance(event, dict) else "")
                or "prediction"
            )
            commence = str(
                market.get("endDate")
                or market.get("end_date")
                or (event.get("startDate") if isinstance(event, dict) else "")
                or ""
            )
            for outcome, raw_probability in zip(outcomes, prices):
                try:
                    probability = float(raw_probability)
                    if not 0 < probability < 1:
                        continue
                    decimal_price = 1 / probability
                    american_price = (
                        round(-100 * probability / (1 - probability))
                        if probability > 0.5
                        else round((decimal_price - 1) * 100)
                    )
                except (TypeError, ValueError, ZeroDivisionError):
                    continue
                records.append(OddsRecord(
                    event_id=market_id,
                    sport="prediction-market",
                    league=category,
                    home_team="Polymarket",
                    away_team=question,
                    commence_time=commence,
                    bookmaker="Polymarket",
                    market="prediction",
                    outcome=str(outcome),
                    price_american=american_price,
                    point=None,
                    observed_at=observed_at,
                    source=self.config.name,
                    category="polymarket",
                ))
        return records


class HtmlOddsConnector:
    """Extract odds from an explicitly permitted public HTML page."""

    def __init__(
        self,
        config: dict[str, Any],
        client: httpx.AsyncClient,
        limiter: PoliteLimiter,
        max_retries: int = 3,
    ) -> None:
        self.config = config
        self.client = client
        self.limiter = limiter
        self.max_retries = max_retries

    async def fetch(self) -> list[OddsRecord]:
        fetcher = JsonOddsConnector(
            OddsConnectorConfig(
                name=self.config["name"],
                url=self.config["url"],
                headers=self.config.get("headers", {}),
                params=self.config.get("params", {}),
            ),
            self.client,
            self.limiter,
            self.max_retries,
        )
        document = await fetcher.fetch_text()
        return self._parse_html(document)

    def _parse_html(self, document: str) -> list[OddsRecord]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(document, "html.parser")
        selectors = self.config.get("selectors", {})
        required = {"event_id", "home_team", "away_team", "outcome", "price"}
        if not required.issubset(selectors):
            raise ValueError(
                "HTML source selectors must include "
                "event_id, home_team, away_team, outcome, and price"
            )
        records: list[OddsRecord] = []
        observed_at = utc_now()
        for element in soup.select(self.config["record_selector"]):
            values = {
                name: element.select_one(selector).get_text(" ", strip=True)
                if element.select_one(selector)
                else ""
                for name, selector in selectors.items()
            }
            try:
                price = int(values["price"].replace("+", ""))
            except (KeyError, TypeError, ValueError):
                continue
            if any(not values.get(name) for name in required):
                continue
            records.append(OddsRecord(
                event_id=values["event_id"],
                sport=self.config.get("sport", "unknown"),
                league=self.config.get("league", "unknown"),
                home_team=values["home_team"],
                away_team=values["away_team"],
                commence_time=values.get("commence_time", ""),
                bookmaker=self.config.get("bookmaker", self.config["name"]),
                market=values.get("market", self.config.get("market", "unknown")),
                outcome=values["outcome"],
                price_american=price,
                point=float(values["point"]) if values.get("point") else None,
                observed_at=observed_at,
                source=self.config["name"],
                category="public-web",
            ))
        return records

async def discover_sports(
    client: httpx.AsyncClient,
    source: dict[str, Any],
    limiter: PoliteLimiter,
    max_retries: int,
) -> list[dict[str, Any]]:
    """Discover every currently available league from an Odds API catalog."""
    catalog_url = source.get(
        "sports_catalog_url",
        "https://api.the-odds-api.com/v4/sports",
    )
    catalog_config = OddsConnectorConfig(
        name=f"{source['name']}-catalog",
        url=catalog_url,
        headers=source.get("headers", {}),
        params=source.get("catalog_params", source.get("params", {})),
        provider="catalog",
    )
    catalog_connector = JsonOddsConnector(
        catalog_config, client, limiter, max_retries
    )
    payload = await catalog_connector.fetch_json()
    if not isinstance(payload, list):
        raise ValueError("sports catalog response must be a list")
    return [sport for sport in payload if isinstance(sport, dict)]


def expand_environment_values(values: dict[str, Any]) -> dict[str, Any]:
    """Expand ${VAR} placeholders in source parameters without storing secrets."""
    expanded: dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            expanded[key] = os.environ.get(value[2:-1], "")
        else:
            expanded[key] = value
    return expanded


class SQLiteStore:
    def __init__(self, path: str | Path = DEFAULT_DB) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS odds_snapshots (
                    fingerprint TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    sport TEXT NOT NULL,
                    league TEXT NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    commence_time TEXT NOT NULL,
                    bookmaker TEXT NOT NULL,
                    market TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    price_american INTEGER NOT NULL,
                    point REAL,
                    observed_at TEXT NOT NULL,
                    source TEXT NOT NULL
                )
            """)
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(odds_snapshots)"
                )
            }
            if "category" not in columns:
                connection.execute(
                    "ALTER TABLE odds_snapshots ADD COLUMN category TEXT "
                    "NOT NULL DEFAULT 'sportsbook'"
                )
            connection.commit()

    def save(self, records: list[OddsRecord]) -> int:
        inserted = 0
        with closing(sqlite3.connect(self.path)) as connection:
            for record in records:
                values = (*asdict(record).values(), record.fingerprint)
                cursor = connection.execute(
                    """INSERT OR IGNORE INTO odds_snapshots
                    (event_id, sport, league, home_team, away_team, commence_time,
                     bookmaker, market, outcome, price_american, point, observed_at,
                     source, category, fingerprint)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    values,
                )
                inserted += cursor.rowcount
            connection.commit()
        return inserted

    def records(self, limit: int = 10_000) -> pd.DataFrame:
        with closing(sqlite3.connect(self.path)) as connection:
            return pd.read_sql_query(
                "SELECT * FROM odds_snapshots ORDER BY observed_at DESC LIMIT ?",
                connection,
                params=(limit,),
            )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def spread_requirement(team: str, point: float | None) -> str:
    """Explain a point spread in plain language for informational display."""
    if point is None:
        return ""
    if point > 0:
        return f"{team} can lose by no more than {point:g}"
    margin = abs(point)
    return f"{team} must win by more than {margin:g}"


def american_to_probability(price: int) -> float:
    if price == 0:
        raise ValueError("American odds cannot be zero")
    return abs(price) / (abs(price) + 100) if price < 0 else 100 / (price + 100)


def calculate_bears_titans_parlay(frame: pd.DataFrame) -> dict[str, Any]:
    """Calculate an informational estimate from the freshest matching lines."""
    legs = {
        "bears_spread_plus_2": {"market": "spreads", "team": "Bears", "point": 2.0},
        "titans_spread_minus_2_5": {"market": "spreads", "team": "Titans", "point": -2.5},
        "over_37_5": {"market": "totals", "outcome": "Over", "point": 37.5},
        "chicago_bears_moneyline": {"market": "h2h", "team": "Bears"},
    }
    result: dict[str, Any] = {
        "informational_only": True,
        "event": "Chicago Bears vs Tennessee Titans",
        "legs": {},
        "available": False,
        "note": "Uses implied probabilities from the freshest matching source rows; no wager is placed.",
    }
    if frame.empty:
        result["message"] = "No source odds are available for this event."
        return result

    data = frame.copy()
    data["observed_at"] = pd.to_datetime(data["observed_at"], utc=True, errors="coerce")
    data["home_team"] = data["home_team"].fillna("").astype(str)
    data["away_team"] = data["away_team"].fillna("").astype(str)
    for name, criteria in legs.items():
        candidates = data[data["market"] == criteria["market"]]
        candidates = candidates[
            candidates["home_team"].str.contains("Bears|Chicago", case=False, regex=True)
            & candidates["away_team"].str.contains("Titans|Tennessee", case=False, regex=True)
        ]
        if "team" in criteria:
            candidates = candidates[candidates["outcome"].str.contains(criteria["team"], case=False, na=False)]
        if "outcome" in criteria:
            candidates = candidates[candidates["outcome"].str.casefold() == criteria["outcome"].casefold()]
        if "point" in criteria:
            candidates = candidates[(candidates["point"] - criteria["point"]).abs() < 0.01]
        candidates = candidates.sort_values("observed_at", ascending=False)
        if candidates.empty:
            result["legs"][name] = {"available": False}
            continue
        row = candidates.iloc[0]
        price = int(row["price_american"])
        result["legs"][name] = {
            "available": True,
            "price_american": price,
            "implied_probability": round(american_to_probability(price), 6),
            "bookmaker": str(row["bookmaker"]),
            "source": str(row["source"]),
            "observed_at": row["observed_at"].isoformat(),
            "point": None if pd.isna(row["point"]) else float(row["point"]),
        }

    available_legs = [leg for leg in result["legs"].values() if leg.get("available")]
    result["available"] = len(available_legs) == len(legs)
    if result["available"]:
        result["combined_implied_probability"] = round(
            float(np.prod([leg["implied_probability"] for leg in available_legs])),
            8,
        )
        result["combined_implied_percent"] = round(
            result["combined_implied_probability"] * 100, 4
        )
    else:
        result["message"] = "Waiting for current Bears/Titans rows from a configured permitted feed."
    return result


def probability_to_decimal(probability: float) -> float:
    if not 0 < probability <= 1:
        raise ValueError("probability must be between 0 and 1")
    return 1 / probability


def no_vig_probabilities(prices: list[int]) -> list[float]:
    implied = np.array([american_to_probability(price) for price in prices], dtype=float)
    total = implied.sum()
    if total <= 0:
        raise ValueError("odds probabilities have no usable mass")
    return (implied / total).tolist()


def analyze_odds(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "records": 0,
            "events": [],
            "categories": {},
            "line_movements": [],
            "anomalies": [],
        }
    data = frame.copy()
    data["implied_probability"] = data["price_american"].map(american_to_probability)
    data["observed_at"] = pd.to_datetime(data["observed_at"], utc=True, errors="coerce")
    data = data.dropna(subset=["observed_at"])
    movements = []
    grouped = data.sort_values("observed_at").groupby(
        ["event_id", "bookmaker", "market", "outcome"], dropna=False
    )
    for group_key, group in grouped:
        if len(group) < 2:
            continue
        first = int(group.iloc[0]["price_american"])
        latest = int(group.iloc[-1]["price_american"])
        if first != latest:
            movements.append({
                "event_id": group_key[0],
                "bookmaker": group_key[1],
                "market": group_key[2],
                "outcome": group_key[3],
                "opening_price": first,
                "latest_price": latest,
                "observations": len(group),
            })
    probabilities = data["implied_probability"].to_numpy(dtype=float)
    mean = float(np.mean(probabilities))
    std = float(np.std(probabilities))
    anomalies = []
    if std > 0:
        data["z_score"] = (data["implied_probability"] - mean) / std
        unusual = data.loc[data["z_score"].abs() >= 2.5]
        anomalies = unusual[["event_id", "bookmaker", "market", "outcome", "z_score"]].to_dict("records")
    events = sorted(data["event_id"].dropna().unique().tolist())
    categories = {
        str(category): int(count)
        for category, count in data["category"].value_counts().items()
    }
    return {
        "records": int(len(data)),
        "events": events,
        "categories": categories,
        "average_implied_probability": round(mean, 6),
        "line_movements": movements,
        "anomalies": anomalies,
    }


def compare_strategies(
    model_probability: float,
    prices: list[int],
    strategy: str = "straight",
) -> dict[str, Any]:
    """Compare hypothetical informational strategies; no wager is placed."""
    if not 0 < model_probability < 1:
        raise ValueError("model_probability must be between 0 and 1")
    fair_decimal = probability_to_decimal(model_probability)
    market_fair = no_vig_probabilities(prices)
    market_probability = float(np.mean(market_fair))
    edge = model_probability - market_probability
    if strategy == "parlay":
        combined_market_probability = float(np.prod(market_fair))
        value_score = model_probability**len(prices) - combined_market_probability
    elif strategy == "hedge":
        value_score = 1 - abs(edge)
    elif strategy in {"straight", "player_prop"}:
        value_score = edge
    else:
        raise ValueError("strategy must be straight, player_prop, parlay, or hedge")
    return {
        "strategy": strategy,
        "informational_only": True,
        "model_probability": round(model_probability, 6),
        "market_fair_probability": round(market_probability, 6),
        "fair_decimal_price": round(fair_decimal, 4),
        "value_score": round(float(value_score), 6),
        "note": "Value score is an analytical comparison, not wagering advice.",
    }


def cashout_ev(
    win_probability: float,
    potential_payout: float,
    cashout_offer: float,
) -> dict[str, Any]:
    """Compare an informational cashout offer with modeled final settlement."""
    if not 0 <= win_probability <= 1 or potential_payout < 0 or cashout_offer < 0:
        raise ValueError("probability and monetary inputs must be non-negative and bounded")
    ride_ev = win_probability * potential_payout
    advantage = cashout_offer - ride_ev
    return {
        "informational_only": True,
        "modeled_ride_out_ev": round(ride_ev, 2),
        "cashout_offer": round(cashout_offer, 2),
        "cashout_minus_ride_ev": round(advantage, 2),
        "model_suggests": "cashout higher" if advantage > 0 else "ride-out EV higher or equal",
        "warning": "Model uncertainty, fees, settlement rules, and live-data delay are excluded.",
    }


async def collect_once(config: dict[str, Any], store: SQLiteStore) -> dict[str, Any]:
    limiter = PoliteLimiter(float(config.get("requests_per_second", 1.0)))
    user_agents = config.get("user_agents", ["SportsAnalyticsLocal/1.0"])
    discovery_failures: list[str] = []
    async with httpx.AsyncClient(timeout=float(config.get("timeout_seconds", 20)), follow_redirects=True) as client:
        connectors = []
        for source in config.get("sources", []):
            if not source.get("enabled", True):
                continue
            headers = dict(source.get("headers", {}))
            headers.setdefault("User-Agent", random.choice(user_agents))
            params = expand_environment_values(source.get("params", {}))
            if source.get("format") == "html":
                connectors.append(
                    HtmlOddsConnector(
                        {**source, "headers": headers, "params": params},
                        client,
                        limiter,
                        int(config.get("max_retries", 3)),
                    )
                )
                continue
            if source.get("provider") == "kalshi":
                try:
                    from kalshi_connector import KalshiMarketConnector

                    connectors.append(
                        KalshiMarketConnector(
                            client,
                            limiter,
                            url=source.get("url"),
                            max_retries=int(config.get("max_retries", 3)),
                            limit=int(source.get("limit", 100)),
                        )
                    )
                except (ImportError, RuntimeError, TypeError, ValueError) as error:
                    discovery_failures.append(str(error))
                continue
            base_config = OddsConnectorConfig(
                name=source["name"],
                url=source["url"],
                sport=source.get("sport", "unknown"),
                headers=headers,
                params=params,
                provider=source.get("provider", "odds"),
            )
            if source.get("all_sports"):
                try:
                    catalog = await discover_sports(
                        client,
                        {**source, "headers": headers, "params": params},
                        limiter,
                        int(config.get("max_retries", 3)),
                    )
                except (httpx.HTTPError, RuntimeError, ValueError, TypeError, KeyError) as error:
                    discovery_failures.append(str(error))
                    continue
                for sport in catalog:
                    sport_key = sport.get("key")
                    if not sport_key:
                        continue
                    url = source["url"].replace("{sport_key}", str(sport_key))
                    connectors.append(JsonOddsConnector(
                        OddsConnectorConfig(
                            name=f"{source['name']}:{sport_key}",
                            url=url,
                            sport=str(sport_key),
                            headers=headers,
                            params=params,
                            provider="odds",
                        ),
                        client,
                        limiter,
                        int(config.get("max_retries", 3)),
                    ))
            else:
                connectors.append(JsonOddsConnector(
                    base_config, client, limiter, int(config.get("max_retries", 3))
                ))
        results = await asyncio.gather(*(connector.fetch() for connector in connectors), return_exceptions=True)
    records: list[OddsRecord] = []
    failures = list(discovery_failures)
    for result in results:
        if isinstance(result, Exception):
            failures.append(str(result))
        else:
            records.extend(result)
    inserted = store.save(records)
    return {"fetched": len(records), "inserted": inserted, "failures": failures}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    with args.config.open("r", encoding="utf-8") as stream:
        config = json.load(stream)
    store = SQLiteStore(args.db)
    while True:
        result = asyncio.run(collect_once(config, store))
        LOGGER.info("Collection result: %s", result)
        if args.once:
            return 0 if not result["failures"] else 2
        time.sleep(max(1, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
