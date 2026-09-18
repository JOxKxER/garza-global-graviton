"""TradeAssist market data ingestion.

Fetches OHLCV bars via yfinance. If the network is unavailable (Wi-Fi off,
DNS failure, timeout, etc.) the fetch is caught cleanly and a locally
simulated pandas DataFrame is returned instead, so the app stays fully
functional offline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import yfinance as yf


def _simulated_data(periods: int = 30, start_price: float = 100.0, seed: int = 42) -> pd.DataFrame:
    """Deterministic local fallback matching the OHLCV shape yfinance returns."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(loc=0.0005, scale=0.01, size=periods)
    close = start_price * np.exp(np.cumsum(returns))
    high = close * (1 + np.abs(rng.normal(0, 0.005, periods)))
    low = close * (1 - np.abs(rng.normal(0, 0.005, periods)))
    open_ = np.concatenate([[start_price], close[:-1]])
    volume = rng.integers(1_000_000, 5_000_000, periods)

    index = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=periods, name="Date")
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=index,
    )


def fetch_market_data(symbol: str = "AAPL", period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
    """Fetch OHLCV data for ``symbol``; fall back to simulated data offline."""
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if df is None or df.empty:
            # yfinance often returns an empty frame instead of raising when
            # the network is down -- treat that as a failure too.
            raise ConnectionError(f"No data returned for {symbol}")
        return df
    except (ConnectionError, TimeoutError, OSError, ValueError) as exc:
        print(f"[data_ingestion] Network fetch failed ({exc}); using simulated data.")
        return _simulated_data()
    except Exception as exc:  # yfinance wraps some network errors in its own types
        print(f"[data_ingestion] Unexpected fetch error ({exc}); using simulated data.")
        return _simulated_data()
