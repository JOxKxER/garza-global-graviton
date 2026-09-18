"""Quantitative, informational-only sports modeling and public-data ingestion."""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
import numpy as np
import pandas as pd

LOGGER = logging.getLogger("sports_modeling")


@dataclass(frozen=True)
class PublicDataSource:
    name: str
    url: str
    kind: str
    params: dict[str, str] | None = None
    headers: dict[str, str] | None = None


@dataclass(frozen=True)
class TeamBaseline:
    team: str
    opponent: str
    offense_rating: float
    defense_rating: float
    recent_win_rate: float
    injury_adjustment: float = 0.0
    sentiment: float = 0.0
    market_liability: float = 0.0


def score_public_headlines(headlines: list[dict[str, Any]]) -> dict[str, float]:
    """Create a bounded, low-weight sentiment score from public headlines."""
    positive = {"win", "surge", "healthy", "favorite", "strong", "breakout"}
    negative = {"loss", "injury", "out", "doubtful", "struggle", "slump"}
    scores: dict[str, list[float]] = {}
    for headline in headlines:
        if not isinstance(headline, dict):
            continue
        team = str(headline.get("team", "")).strip()
        text = str(headline.get("title", headline.get("text", ""))).casefold()
        if not team or not text:
            continue
        value = sum(word in text for word in positive) - sum(
            word in text for word in negative
        )
        scores.setdefault(team, []).append(float(np.clip(value / 3, -1, 1)))
    return {
        team: float(np.clip(np.mean(values), -1, 1))
        for team, values in scores.items()
    }


def aggregate_player_statistics(
    rows: list[dict[str, Any]],
) -> dict[str, dict[str, float]]:
    """Aggregate bounded historical player metrics into team adjustments."""
    totals: dict[str, list[dict[str, float]]] = {}
    for row in rows:
        if not isinstance(row, dict) or not row.get("team"):
            continue
        team = str(row["team"]).strip()
        totals.setdefault(team, []).append({
            "offense": float(row.get("offense_rating", row.get("points_per_game", 0))),
            "defense": float(row.get("defense_rating", 0)),
            "availability": float(np.clip(row.get("availability", 1), 0, 1)),
        })
    return {
        team: {
            "offense": float(np.clip(np.mean([item["offense"] for item in values]), -20, 20)),
            "defense": float(np.clip(np.mean([item["defense"] for item in values]), -20, 20)),
            "availability": float(np.mean([item["availability"] for item in values])),
        }
        for team, values in totals.items()
    }


def aggregate_coach_statistics(
    rows: list[dict[str, Any]],
) -> dict[str, float]:
    """Convert historical coach records into a bounded win-rate adjustment."""
    adjustments: dict[str, list[float]] = {}
    for row in rows:
        if not isinstance(row, dict) or not row.get("team"):
            continue
        team = str(row["team"]).strip()
        win_rate = float(row.get("win_rate", 0.5))
        adjustments.setdefault(team, []).append(float(np.clip(win_rate, 0, 1)))
    return {
        team: float(np.mean(values) - 0.5)
        for team, values in adjustments.items()
    }


def estimate_event(
    home_team: str,
    away_team: str,
    event_date: str,
    home_stats: dict[str, float] | None = None,
    away_stats: dict[str, float] | None = None,
    injuries: dict[str, float] | None = None,
    sentiment: dict[str, float] | None = None,
    player_statistics: dict[str, dict[str, float]] | None = None,
    coach_statistics: dict[str, float] | None = None,
    market_probability: float | None = None,
    simulations: int = 10_000,
) -> dict[str, Any]:
    """Model a user-selected event from supplied public/statistical inputs."""
    home_stats = home_stats or {}
    away_stats = away_stats or {}
    injuries = injuries or {}
    sentiment = sentiment or {}
    player_statistics = player_statistics or {}
    coach_statistics = coach_statistics or {}
    home_player = player_statistics.get(home_team, {})
    away_player = player_statistics.get(away_team, {})
    home_coach = coach_statistics.get(home_team, 0.0)
    away_coach = coach_statistics.get(away_team, 0.0)
    home = TeamBaseline(
        home_team,
        away_team,
        float(home_stats.get("offense_rating", 100)) + home_player.get("offense", 0),
        float(home_stats.get("defense_rating", 100)) + home_player.get("defense", 0),
        float(home_stats.get("recent_win_rate", 0.5)),
        injuries.get(home_team, 0),
        sentiment.get(home_team, 0) + home_coach,
    )
    away = TeamBaseline(
        away_team,
        home_team,
        float(away_stats.get("offense_rating", 100)) + away_player.get("offense", 0),
        float(away_stats.get("defense_rating", 100)) + away_player.get("defense", 0),
        float(away_stats.get("recent_win_rate", 0.5)),
        injuries.get(away_team, 0),
        sentiment.get(away_team, 0) + away_coach,
    )
    result = model_matchup(
        home,
        away,
        market_probability=market_probability,
        simulations=simulations,
    )
    result["event_date"] = event_date
    result["source_inputs"] = {
        "historical_stats": bool(home_stats or away_stats),
        "injury_reports": bool(injuries),
        "public_sentiment": bool(sentiment),
        "player_statistics": bool(player_statistics),
        "coach_statistics": bool(coach_statistics),
    }
    result["historical_context"] = {
        "home_player": home_player,
        "away_player": away_player,
        "home_coach_adjustment": home_coach,
        "away_coach_adjustment": away_coach,
    }
    return result


def calculate_parlay_probability(legs: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate a transparent product estimate for user-entered event legs."""
    if not legs:
        raise ValueError("at least one parlay leg is required")
    probabilities = []
    normalized = []
    for leg in legs:
        probability = float(leg.get("probability", 0))
        if not 0 < probability <= 1:
            raise ValueError("each leg probability must be between 0 and 1")
        probabilities.append(probability)
        normalized.append({
            "label": str(leg.get("label", "Unnamed leg")),
            "probability": round(probability, 6),
        })
    combined = float(np.prod(probabilities))
    return {
        "legs": normalized,
        "combined_probability": round(combined, 8),
        "combined_percent": round(combined * 100, 4),
        "assumption": "Legs are treated as independent; correlation and model error are not estimated.",
        "informational_only": True,
    }


class PublicDataHarvester:
    """Fetch permitted public JSON sources with bounded concurrency and retries."""

    def __init__(
        self,
        timeout_seconds: float = 20.0,
        requests_per_second: float = 1.0,
        max_retries: int = 3,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.interval = 1.0 / requests_per_second
        self._next_request = 0.0
        self._rate_lock = asyncio.Lock()

    async def _wait(self) -> None:
        async with self._rate_lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            delay = max(0.0, self._next_request - now)
            self._next_request = max(now, self._next_request) + self.interval
        if delay:
            await asyncio.sleep(delay + random.uniform(0, self.interval * 0.2))

    async def fetch(self, client: httpx.AsyncClient, source: PublicDataSource) -> dict[str, Any] | list[Any]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            await self._wait()
            try:
                response = await client.get(
                    source.url,
                    params=source.params or {},
                    headers=source.headers or {"User-Agent": "GravitonSportsAnalytics/1.0"},
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, (dict, list)):
                    raise ValueError("public source did not return JSON object/list")
                return payload
            except (httpx.HTTPError, ValueError, TypeError) as error:
                last_error = error
                if attempt >= self.max_retries:
                    break
                await asyncio.sleep(min(60.0, 2**attempt + random.random()))
        raise RuntimeError(f"public source failed: {source.name}") from last_error

    async def collect(self, sources: list[PublicDataSource]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
            results = await asyncio.gather(
                *(self.fetch(client, source) for source in sources),
                return_exceptions=True,
            )
        collected: dict[str, Any] = {}
        for source, result in zip(sources, results):
            if isinstance(result, Exception):
                LOGGER.warning("%s: %s", source.name, result)
                continue
            collected[source.kind] = result
        return collected


def normalize_historical_games(payload: Any) -> pd.DataFrame:
    """Normalize public game-log rows into a small modeling baseline table."""
    rows = payload.get("games", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return pd.DataFrame()
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        normalized.append({
            "team": str(row.get("team", "")).strip(),
            "opponent": str(row.get("opponent", "")).strip(),
            "won": float(bool(row.get("won", False))),
            "point_diff": float(row.get("point_diff", 0.0)),
            "offense_rating": float(row.get("offense_rating", 100.0)),
            "defense_rating": float(row.get("defense_rating", 100.0)),
        })
    return pd.DataFrame(normalized)


def normalize_injuries(payload: Any) -> dict[str, float]:
    """Convert public injury reports into bounded team adjustments."""
    rows = payload.get("injuries", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return {}
    adjustments: dict[str, float] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        team = str(row.get("team", "")).strip()
        status = str(row.get("status", "")).casefold()
        impact = float(row.get("impact", 1.0))
        if team and status in {"out", "ir", "doubtful"}:
            adjustments[team] = adjustments.get(team, 0.0) - min(10.0, max(0.0, impact))
    return adjustments


def normalize_sentiment(payload: Any) -> dict[str, float]:
    """Bound public sentiment scores to -1..1 by team."""
    rows = payload.get("sentiment", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return {}
    result = {}
    for row in rows:
        if isinstance(row, dict) and row.get("team"):
            result[str(row["team"])] = float(np.clip(row.get("score", 0.0), -1.0, 1.0))
    return result


def build_baselines(
    games: pd.DataFrame,
    injuries: dict[str, float] | None = None,
    sentiment: dict[str, float] | None = None,
) -> dict[str, TeamBaseline]:
    """Aggregate historical games and public context into team baselines."""
    if games.empty:
        return {}
    injuries = injuries or {}
    sentiment = sentiment or {}
    baselines = {}
    for team, group in games.groupby("team"):
        baselines[team] = TeamBaseline(
            team=team,
            opponent=str(group["opponent"].mode().iloc[0]) if not group["opponent"].mode().empty else "",
            offense_rating=float(group["offense_rating"].mean()),
            defense_rating=float(group["defense_rating"].mean()),
            recent_win_rate=float(group["won"].tail(10).mean()),
            injury_adjustment=injuries.get(team, 0.0),
            sentiment=sentiment.get(team, 0.0),
        )
    return baselines


def model_matchup(
    home: TeamBaseline,
    away: TeamBaseline,
    market_probability: float | None = None,
    simulations: int = 10_000,
    seed: int = 42,
) -> dict[str, Any]:
    """Estimate win probabilities using ratings, context, and Monte Carlo outcomes."""
    if simulations < 100 or not 0 <= (market_probability or 0.5) <= 1:
        raise ValueError("simulations must be >=100 and market_probability must be bounded")
    rng = np.random.default_rng(seed)
    home_strength = (
        home.offense_rating - away.defense_rating
        + 8 * (home.recent_win_rate - away.recent_win_rate)
        + home.injury_adjustment - away.injury_adjustment
        + 2 * (home.sentiment - away.sentiment)
    )
    away_strength = (
        away.offense_rating - home.defense_rating
        + 8 * (away.recent_win_rate - home.recent_win_rate)
        + away.injury_adjustment - home.injury_adjustment
        + 2 * (away.sentiment - home.sentiment)
    )
    home_score = rng.normal(100 + home_strength, 12, simulations)
    away_score = rng.normal(100 + away_strength, 12, simulations)
    home_probability = float(np.mean(home_score > away_score))
    if market_probability is not None:
        home_probability = float(np.clip(0.75 * home_probability + 0.25 * market_probability, 0.01, 0.99))
    away_probability = 1 - home_probability
    return {
        "home_team": home.team,
        "away_team": away.team,
        "home_win_probability": round(home_probability, 6),
        "away_win_probability": round(away_probability, 6),
        "simulations": simulations,
        "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "informational_only": True,
        "market_context": market_probability,
        "warning": "Model output is uncertain informational analysis, not wagering advice.",
    }


def generate_predictions(
    games: pd.DataFrame,
    injuries: dict[str, float] | None = None,
    sentiment: dict[str, float] | None = None,
    odds: pd.DataFrame | None = None,
    player_statistics: dict[str, dict[str, float]] | None = None,
    coach_statistics: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Generate predictions for each matchup represented in public game logs."""
    baselines = build_baselines(games, injuries, sentiment)
    predictions = []
    for baseline in baselines.values():
        opponent = baselines.get(baseline.opponent)
        if opponent is None or baseline.team >= opponent.team:
            continue
        market_probability = None
        if odds is not None and not odds.empty:
            market_probability = float(odds.loc[odds["outcome"] == baseline.team, "implied_probability"].mean())
            if np.isnan(market_probability):
                market_probability = None
        predictions.append(
            estimate_event(
                baseline.team,
                opponent.team,
                "",
                home_stats={
                    "offense_rating": baseline.offense_rating,
                    "defense_rating": baseline.defense_rating,
                    "recent_win_rate": baseline.recent_win_rate,
                },
                away_stats={
                    "offense_rating": opponent.offense_rating,
                    "defense_rating": opponent.defense_rating,
                    "recent_win_rate": opponent.recent_win_rate,
                },
                injuries=injuries,
                sentiment=sentiment,
                player_statistics=player_statistics,
                coach_statistics=coach_statistics,
                market_probability=market_probability,
            )
        )
    return predictions
