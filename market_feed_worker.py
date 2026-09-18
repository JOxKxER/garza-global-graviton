"""Async market ticker ingestion and local Joker signal analysis worker."""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import time
import uuid
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiohttp
import yfinance as yf

try:
    from .src.dual_plane_runtime import DualPlaneRuntime
except ImportError:
    from src.dual_plane_runtime import DualPlaneRuntime


DEFAULT_DB_PATH = (
    Path(__file__).resolve().parent / "data_in" / "mesh_telemetry.db"
)
DEFAULT_JOKER_URL = "http://127.0.0.1:8011/v1/chat/completions"
DEFAULT_JOKER_MODEL = "ggml-org/Qwen2.5-Coder-7B-Instruct-Q8_0-GGUF"
DEFAULT_ACCOUNT_BALANCE = 100.0
DEFAULT_MAX_RISK_PERCENT = 2.0
DEFAULT_POLL_INTERVAL_SECONDS = 15.0
YFINANCE_TIMEOUT_SECONDS = 5.0
MACRO_SYMBOLS = ["SPY", "QQQ", "VIXY", "XLK", "XLF", "XLP", "XLU"]
TACTICAL_GROUPS = {
    "high_beta_tech": {"symbols": {"NVDA", "AMD", "TSLA", "PLTR"}},
    "defensive_proxies": {"symbols": {"XLP", "XLU", "JNJ", "PG"}},
    "high_volume_momentum": {"symbols": set()},
}
JOKER_MARKET_SYSTEM_PROMPT = (
    "You are Joker, a local market analyst using a "
    "Glacier-to-Ripple framework "
    "for a strict $100 micro-account. Macro glaciers are slow institutional "
    "forces: capital reallocation, regulation, supply-chain shifts, and "
    "sector "
    "crises. Do not pretend a $100 account can ride the glacier directly. "
    "Instead, identify localized collateral impacts, panic dips, and "
    "structural "
    "mispricings that may create asymmetric rebound windows. This is "
    "informational analysis, not financial advice, and never imply certainty. "
    "Scan anomalies, volume surges, sector distress, severe oversold "
    "readings, "
    "regulatory shock overreactions, and essential-infrastructure recovery or "
    "safety-net evidence. Distinguish a structural catalyst from ordinary "
    "noise. Assume fractional shares: calculate shares from dollar risk "
    "divided by stop distance, never recommend a whole-share position above "
    "account value, and "
    "cap risk at 1% to 2% ($1 to $2). Prefer no trade when liquidity, spread, "
    "catalyst credibility, timing, or stop placement is inadequate."
)


@dataclass(frozen=True)
class Ticker:
    symbol: str
    price: float
    change_percent: float | None
    volume: int | None
    market_state: str | None
    observed_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "change_percent": self.change_percent,
            "volume": self.volume,
            "market_state": self.market_state,
            "observed_at": self.observed_at,
        }


class MarketFeedWorker:
    def __init__(
        self,
        symbols: list[str],
        db_path: Path = DEFAULT_DB_PATH,
        joker_url: str = DEFAULT_JOKER_URL,
        joker_model: str = DEFAULT_JOKER_MODEL,
        interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        account_balance: float = DEFAULT_ACCOUNT_BALANCE,
        max_risk_percent: float = DEFAULT_MAX_RISK_PERCENT,
    ) -> None:
        if account_balance <= 0:
            raise ValueError("account_balance must be greater than zero")
        if not 1.0 <= max_risk_percent <= 2.0:
            raise ValueError("max_risk_percent must be between 1% and 2%")
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than zero")
        self.symbols = [symbol.upper() for symbol in symbols]
        self.db_path = Path(db_path)
        self.joker_url = joker_url
        self.joker_model = joker_model
        self.interval_seconds = interval_seconds
        self.account_balance = account_balance
        self.max_risk_percent = max_risk_percent
        self.execution_runtime = DualPlaneRuntime()
        self._stop_event = asyncio.Event()

    async def run_once(self) -> dict[str, Any]:
        """Fetch, persist, and analyze the Glacier-to-Micro snapshot."""
        async with aiohttp.ClientSession() as session:
            tickers = await self.fetch_tickers(session)
            macro = await self.fetch_macro_snapshot()
            runtime_metrics = self.project_execution_surface(tickers, macro)
            await asyncio.to_thread(self.persist_tickers, tickers)
            analysis = await self.query_joker(session, tickers, macro)

        result = {
            "observed_at": datetime.now(UTC).isoformat(),
            "tickers": [ticker.as_dict() for ticker in tickers],
            "macro": macro,
            "analysis": analysis,
            "runtime": runtime_metrics,
        }
        await asyncio.to_thread(self.persist_analysis, result)
        return result

    async def run_forever(self) -> None:
        while not self._stop_event.is_set():
            started = time.monotonic()
            try:
                result = await self.run_once()
                print(json.dumps(result, indent=2))
            except (
                aiohttp.ClientError,
                OSError,
                RuntimeError,
                ValueError,
            ) as error:
                print(f"Market feed cycle failed: {error}")

            remaining = self.interval_seconds - (time.monotonic() - started)
            if remaining > 0:
                with suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(self._stop_event.wait(), remaining)

    def stop(self) -> None:
        self._stop_event.set()

    async def fetch_tickers(
        self, session: aiohttp.ClientSession
    ) -> list[Ticker]:
        del session
        try:
            history = await asyncio.wait_for(
                asyncio.to_thread(
                    yf.download,
                    tickers=self.symbols,
                    period="1d",
                    interval="1m",
                    group_by="ticker",
                    auto_adjust=False,
                    progress=False,
                    threads=False,
                ),
                timeout=YFINANCE_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError as error:
            raise RuntimeError(
                "yfinance history fetch timed out after "
                f"{YFINANCE_TIMEOUT_SECONDS:g} seconds"
            ) from error
        tickers: list[Ticker] = []
        observed_at = datetime.now(UTC).isoformat()
        for symbol in self.symbols:
            symbol_history = _select_symbol_history(history, symbol)
            if symbol_history is None:
                continue

            closes = _numeric_series(symbol_history, "Close")
            if closes is None or closes.empty:
                continue
            price = float(closes.iloc[-1])
            previous_close = (
                float(closes.iloc[-2]) if len(closes) > 1 else None
            )
            change_percent = None
            if previous_close:
                change_percent = (
                    (price - previous_close) / previous_close
                ) * 100
            volume = _numeric_series(symbol_history, "Volume")
            tickers.append(
                Ticker(
                    symbol=symbol,
                    price=price,
                    change_percent=change_percent,
                    volume=(
                        int(volume.iloc[-1])
                        if volume is not None and volume.size
                        else None
                    ),
                    market_state=None,
                    observed_at=observed_at,
                )
            )

        if not tickers:
            raise RuntimeError("yfinance returned no usable ticker data")
        return tickers

    def project_execution_surface(
        self,
        tickers: list[Ticker],
        macro: dict[str, Any],
    ) -> dict[str, Any]:
        """Stream a market tensor through the fast execution plane."""
        changes = [ticker.change_percent or 0.0 for ticker in tickers]
        volumes = [float(ticker.volume or 0) for ticker in tickers]
        macro_changes = [
            item.get("change_percent") or 0.0
            for item in macro.get("benchmarks", [])
        ]
        features = [
            sum(changes) / max(1, len(changes)),
            sum(volumes) / max(1, len(volumes)) / 1_000_000,
            sum(macro_changes) / max(1, len(macro_changes)),
        ]
        risk_budget = self.account_balance * self.max_risk_percent / 100
        surface = self.execution_runtime.project_market_tensor(
            features, risk_budget
        )
        fallback = self.execution_runtime.route_with_failover(
            source=(0.0, 0.0),
            target=(surface.torus.x, surface.torus.y),
            endpoints=("joker_local", "cached_local", "offline_safe"),
            congestion=(abs(features[0]), abs(features[1])),
        )
        return {
            "plane": "fast_surface",
            "tensor_features": features,
            "toroidal_coordinate": {
                "x": surface.torus.x,
                "y": surface.torus.y,
            },
            "quadratic_execution": {
                "entry_score": surface.entry_score,
                "exit_score": surface.exit_score,
                "energy": surface.energy,
                "risk_budget": surface.risk_budget,
            },
            "mesh_route": {
                "selected_endpoint": fallback.endpoint,
                "attempted_endpoints": fallback.attempted,
                "route_energy": fallback.route.energy,
            },
        }

    async def fetch_macro_snapshot(self) -> dict[str, Any]:
        """Fetch benchmarks plus a slower 60-day historical baseline."""
        history = await asyncio.wait_for(
            asyncio.to_thread(
                yf.download,
                tickers=MACRO_SYMBOLS,
                period="60d",
                interval="1d",
                group_by="ticker",
                auto_adjust=False,
                progress=False,
                threads=False,
            ),
            timeout=YFINANCE_TIMEOUT_SECONDS,
        )
        benchmarks: list[dict[str, Any]] = []
        for symbol in MACRO_SYMBOLS:
            frame = _select_symbol_history(history, symbol)
            closes = (
                _numeric_series(frame, "Close") if frame is not None else None
            )
            if closes is None or closes.empty:
                continue
            latest = float(closes.iloc[-1])
            baseline = float(closes.mean())
            prior = float(closes.iloc[-2]) if len(closes) > 1 else None
            benchmarks.append(
                {
                    "symbol": symbol,
                    "latest": latest,
                    "baseline_60d": baseline,
                    "distance_from_baseline_percent": (
                        ((latest - baseline) / baseline * 100)
                        if baseline
                        else None
                    ),
                    "change_percent": (
                        (latest - prior) / prior * 100
                        if prior
                        else None
                    ),
                }
            )
        if not benchmarks:
            raise RuntimeError("No macro benchmark data returned by yfinance")
        return {"benchmarks": benchmarks, "symbols": MACRO_SYMBOLS}

    async def query_joker(
        self,
        session: aiohttp.ClientSession,
        tickers: list[Ticker],
        macro: dict[str, Any],
    ) -> dict[str, Any]:
        snapshot = json.dumps(
            [ticker.as_dict() for ticker in tickers], indent=2
        )
        max_risk_dollars = (
            self.account_balance * self.max_risk_percent / 100
        )
        groups = _build_subgroups(tickers)
        payload = {
            "model": self.joker_model,
            "messages": [
                {
                    "role": "system",
                    "content": JOKER_MARKET_SYSTEM_PROMPT
                    + " Return JSON only with keys macro_outlook, "
                    "structural_rebound_watch, subgroups, and micro_actions.",
                },
                {
                    "role": "user",
                    "content": (
                        "Evaluate this live market snapshot. Identify notable "
                        "signals, market conditions, and risks without "
                        "issuing an order. Include: signal quality, liquidity "
                        "concerns, fractional entry size, stop distance, "
                        "dollar risk, and a no-trade rationale when "
                        "appropriate. "
                        "For each structural candidate include catalyst type, "
                        "distress evidence, recovery probability, "
                        "invalidation, "
                        "and the precise panic-dip timing window. "
                        f"Account balance: ${self.account_balance:.2f}; "
                        f"maximum risk: {self.max_risk_percent:.1f}% "
                        f"($"
                        f"{max_risk_dollars:.2f})"
                        ".\n"
                        "Macro Glacier baseline:\n"
                        f"{json.dumps(macro, indent=2)}\n"
                        "Tactical Fracture Zones:\n"
                        f"{json.dumps(groups, indent=2)}\n"
                        f"Micro snapshot:\n{snapshot}"
                    ),
                },
            ],
            "stream": False,
            "temperature": 0.1,
            "max_tokens": 512,
        }
        async with session.post(self.joker_url, json=payload) as response:
            response.raise_for_status()
            result = await response.json()
        try:
            content = str(result["choices"][0]["message"]["content"]).strip()
            return _parse_joker_analysis(content)
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError(
                f"Unexpected Joker response: {result!r}"
            ) from error

    def persist_tickers(self, tickers: list[Ticker]) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path, timeout=30) as connection:
            journal_mode = connection.execute(
                "PRAGMA journal_mode=WAL"
            ).fetchone()[0]
            if str(journal_mode).lower() != "wal":
                raise RuntimeError(
                    f"Unable to enable SQLite WAL mode: {journal_mode}"
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS market_ticker_telemetry (
                    id TEXT PRIMARY KEY,
                    recorded_at TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    price REAL NOT NULL,
                    change_percent REAL,
                    volume INTEGER,
                    market_state TEXT,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.executemany(
                """
                INSERT INTO market_ticker_telemetry
                (id, recorded_at, symbol, price, change_percent, volume,
                 market_state, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        str(uuid.uuid4()),
                        ticker.observed_at,
                        ticker.symbol,
                        ticker.price,
                        ticker.change_percent,
                        ticker.volume,
                        ticker.market_state,
                        json.dumps(ticker.as_dict()),
                    )
                    for ticker in tickers
                ],
            )
            connection.commit()

    def persist_analysis(self, result: dict[str, Any]) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path, timeout=30) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS macro_market_telemetry (
                    id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL,
                    outlook TEXT NOT NULL, benchmarks_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS subgroup_signal_analysis (
                    id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL,
                    subgroup TEXT NOT NULL, probability REAL,
                    direction TEXT, rationale TEXT, payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS micro_transaction_actionables (
                    id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL,
                    symbol TEXT NOT NULL, action TEXT NOT NULL,
                    entry_price REAL, stop_price REAL, shares REAL,
                    dollar_risk REAL, rationale TEXT,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS structural_rebound_watch (
                    id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL,
                    symbol TEXT NOT NULL, catalyst_type TEXT NOT NULL,
                    distress_evidence TEXT, recovery_probability REAL,
                    timing_window TEXT, invalidation TEXT,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS market_signal_analysis (
                    id TEXT PRIMARY KEY,
                    recorded_at TEXT NOT NULL,
                    analysis TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO market_signal_analysis
                (id, recorded_at, analysis, snapshot_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    result["observed_at"],
                    json.dumps(result["analysis"]),
                    json.dumps(result["tickers"]),
                ),
            )
            analysis = result["analysis"]
            macro_outlook = analysis.get("macro_outlook", "No macro outlook")
            connection.execute(
                "INSERT INTO macro_market_telemetry VALUES (?, ?, ?, ?)",
                (
                    str(uuid.uuid4()), result["observed_at"], macro_outlook,
                    json.dumps(result["macro"]),
                ),
            )
            for watch in analysis.get("structural_rebound_watch", []):
                connection.execute(
                    "INSERT INTO structural_rebound_watch "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid.uuid4()), result["observed_at"],
                        watch.get("symbol", "unknown"),
                        watch.get("catalyst_type", "unknown"),
                        watch.get("distress_evidence", ""),
                        _optional_float(watch.get("recovery_probability")),
                        watch.get("timing_window", "no timing window"),
                        watch.get("invalidation", "no trade if invalidated"),
                        json.dumps(watch),
                    ),
                )
            for subgroup in analysis.get("subgroups", []):
                connection.execute(
                    "INSERT INTO subgroup_signal_analysis "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid.uuid4()), result["observed_at"],
                        subgroup.get("name", "unknown"),
                        _optional_float(subgroup.get("probability")),
                        subgroup.get("direction", "neutral"),
                        subgroup.get("rationale", ""), json.dumps(subgroup),
                    ),
                )
            for action in analysis.get("micro_actions", []):
                connection.execute(
                    "INSERT INTO micro_transaction_actionables "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid.uuid4()), result["observed_at"],
                        action.get("symbol", "unknown"),
                        action.get("action", "no_trade"),
                        _optional_float(action.get("entry_price")),
                        _optional_float(action.get("stop_price")),
                        _optional_float(action.get("shares")),
                        _optional_float(action.get("dollar_risk")),
                        action.get("rationale", ""), json.dumps(action),
                    ),
                )
            connection.commit()


def _as_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _as_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _optional_float(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _build_subgroups(tickers: list[Ticker]) -> list[dict[str, Any]]:
    """Create tactical groups before Joker probabilistic scoring."""
    by_symbol = {ticker.symbol: ticker for ticker in tickers}
    groups: list[dict[str, Any]] = []
    for name, config in TACTICAL_GROUPS.items():
        members = [
            by_symbol[symbol]
            for symbol in config["symbols"]
            if symbol in by_symbol
        ]
        if name == "high_volume_momentum":
            ranked = sorted(
                tickers, key=lambda ticker: ticker.volume or 0, reverse=True
            )
            members = ranked[:5]
        if not members:
            continue
        groups.append(
            {
                "name": name,
                "symbols": [ticker.symbol for ticker in members],
                "average_change_percent": sum(
                    ticker.change_percent or 0 for ticker in members
                ) / len(members),
                "relative_strength_note": (
                    "Compare against SPY and QQQ macro baselines."
                ),
            }
        )
    return groups


def _parse_joker_analysis(content: str) -> dict[str, Any]:
    """Parse Joker output with a safe no-trade fallback."""
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {
            "macro_outlook": content,
            "structural_rebound_watch": [],
            "subgroups": [],
            "micro_actions": [],
        }
    if not isinstance(parsed, dict):
        raise RuntimeError("Joker analysis must be a JSON object")
    return {
        "macro_outlook": str(parsed.get("macro_outlook", "")),
        "structural_rebound_watch": parsed.get(
            "structural_rebound_watch", []
        ),
        "subgroups": parsed.get("subgroups", []),
        "micro_actions": parsed.get("micro_actions", []),
    }


def _select_symbol_history(history: Any, symbol: str) -> Any | None:
    """Return one symbol's OHLCV frame for flat or MultiIndex columns."""
    columns = getattr(history, "columns", None)
    if columns is None:
        return None

    levels = getattr(columns, "nlevels", 1)
    if levels == 1:
        return history

    for level in range(levels):
        values = columns.get_level_values(level)
        if symbol in values:
            try:
                return history.xs(symbol, level=level, axis=1, drop_level=True)
            except KeyError:
                return None
    return None


def _numeric_series(frame: Any, field: str) -> Any | None:
    """Extract a numeric field as a one-dimensional, null-free Series."""
    try:
        values = frame[field]
    except (KeyError, TypeError):
        return None

    if getattr(values, "ndim", 1) > 1:
        values = values.iloc[:, 0]
    return values.dropna()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "symbols", nargs="+", help="Ticker symbols, e.g. AAPL MSFT NVDA"
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--joker-url", default=DEFAULT_JOKER_URL)
    parser.add_argument("--joker-model", default=DEFAULT_JOKER_MODEL)
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help="Polling interval in seconds; default is 15 for intraday checks.",
    )
    parser.add_argument(
        "--account-balance",
        type=float,
        default=DEFAULT_ACCOUNT_BALANCE,
    )
    parser.add_argument(
        "--max-risk-percent",
        type=float,
        default=DEFAULT_MAX_RISK_PERCENT,
    )
    parser.add_argument(
        "--once", action="store_true", help="Run one ingestion cycle"
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    worker = MarketFeedWorker(
        symbols=args.symbols,
        db_path=args.db,
        joker_url=args.joker_url,
        joker_model=args.joker_model,
        interval_seconds=args.interval,
        account_balance=args.account_balance,
        max_risk_percent=args.max_risk_percent,
    )
    if args.once:
        print(json.dumps(await worker.run_once(), indent=2))
    else:
        await worker.run_forever()


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        asyncio.run(main())
