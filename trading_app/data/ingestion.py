"""Data ingestion and local caching layer.

Two data sources are supported, deliberately kept separate:
  1. `generate_synthetic_history()` -- a local, deterministic-if-seeded random
     walk generator. Zero network calls. This is what powers the dry run and
     any offline development/testing.
  2. `fetch_alpaca_bars()` -- an opt-in live/historical fetch via Alpaca's
     market data API. Only imported/used when explicitly called; never runs
     as part of the default dry-run path.

Everything downstream (the probability engine, risk manager) only ever sees
a pandas DataFrame with columns [open, high, low, close, volume] indexed by
timestamp -- it does not care which source produced it.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


class LocalDataCache:
    """Simple on-disk CSV cache, one file per symbol. Keeps the decision
    engine usable fully offline once a symbol's history has been cached."""

    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, symbol: str) -> Path:
        return self.cache_dir / f"{symbol.upper()}.csv"

    def has(self, symbol: str) -> bool:
        return self._path(symbol).is_file()

    def load(self, symbol: str) -> pd.DataFrame:
        return pd.read_csv(self._path(symbol), index_col=0, parse_dates=True)

    def save(self, symbol: str, df: pd.DataFrame) -> None:
        df.to_csv(self._path(symbol))


def generate_synthetic_history(
    symbol: str,
    periods: int = 500,
    start_price: float = 100.0,
    annual_volatility: float = 0.25,
    annual_drift: float = 0.05,
    seed: Optional[int] = None,
) -> pd.DataFrame:
    """Local, offline geometric-Brownian-motion-style daily bar generator.
    Used for the dry run and for exercising the pipeline without any network
    dependency or real market data. NOT a substitute for real historical
    data when evaluating a strategy for live use."""
    rng = np.random.default_rng(seed)
    dt = 1 / 252
    daily_drift = annual_drift * dt
    daily_vol = annual_volatility * np.sqrt(dt)

    returns = rng.normal(loc=daily_drift, scale=daily_vol, size=periods)
    close = start_price * np.exp(np.cumsum(returns))

    # Cheap synthetic OHLC/volume derived from the close series -- fine for
    # exercising indicator math, not a realistic intraday model.
    high = close * (1 + np.abs(rng.normal(0, daily_vol / 2, periods)))
    low = close * (1 - np.abs(rng.normal(0, daily_vol / 2, periods)))
    open_ = np.concatenate([[start_price], close[:-1]])
    volume = rng.integers(1_000_000, 5_000_000, periods)

    index = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=periods)
    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=index
    )
    df.index.name = "timestamp"
    return df


def fetch_alpaca_bars(symbol: str, lookback_days: int = 500, timeframe: str = "1Day") -> pd.DataFrame:
    """Opt-in live historical fetch via Alpaca's market data API. Requires
    ALPACA_API_KEY/ALPACA_SECRET_KEY and the `alpaca-py` package. Imported
    lazily so the rest of this package works with zero extra dependencies
    when you only want the offline/paper pipeline."""
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
    except ImportError as exc:
        raise ImportError(
            "fetch_alpaca_bars() requires the 'alpaca-py' package. "
            "Install it with: pip install alpaca-py"
        ) from exc

    api_key = os.environ.get("ALPACA_API_KEY", "")
    secret_key = os.environ.get("ALPACA_SECRET_KEY", "")
    if not (api_key and secret_key):
        raise RuntimeError("ALPACA_API_KEY / ALPACA_SECRET_KEY must be set to fetch live data.")

    client = StockHistoricalDataClient(api_key, secret_key)
    tf_map = {"1Day": TimeFrame.Day, "1Hour": TimeFrame.Hour, "1Min": TimeFrame.Minute}
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=tf_map.get(timeframe, TimeFrame.Day),
        start=pd.Timestamp.today() - pd.Timedelta(days=lookback_days),
    )
    bars = client.get_stock_bars(request).df
    bars = bars.loc[symbol] if symbol in bars.index.get_level_values(0) else bars
    return bars[["open", "high", "low", "close", "volume"]]


def load_history(symbol: str, cache: LocalDataCache, allow_live_fetch: bool = False) -> pd.DataFrame:
    """Cache-first loader: serves from local CSV if present, otherwise falls
    back to synthetic data (fully offline) unless `allow_live_fetch=True` is
    explicitly passed, in which case it fetches once and caches the result."""
    if cache.has(symbol):
        return cache.load(symbol)
    if allow_live_fetch:
        df = fetch_alpaca_bars(symbol)
    else:
        df = generate_synthetic_history(symbol)
    cache.save(symbol, df)
    return df
