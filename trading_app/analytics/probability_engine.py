"""Probability & analytics engine.

Computes a small set of standard technical indicators (all pure local
pandas/numpy computation over an already-in-memory DataFrame -- no network
calls anywhere in this module) and combines them into a bounded [0, 1]
"success probability" for a mean-reversion + momentum blended signal.

This is a transparent, rule-based heuristic, not a validated source of alpha.
Treat `probability` as a relative confidence score for ranking/sizing
purposes, not a literal statistical guarantee -- backtest thoroughly on real
historical data for your actual universe before trusting it with real
capital.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd


class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class Signal:
    action: Action
    probability: float  # bounded [0, 1]; see module docstring caveat
    edge: float  # signed strength, roughly in [-1, 1], used for Kelly sizing
    price: float
    reasons: list


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["sma_20"] = out["close"].rolling(20).mean()
    out["sma_50"] = out["close"].rolling(50).mean()
    out["daily_return"] = out["close"].pct_change()
    out["volatility_20"] = out["daily_return"].rolling(20).std()

    # RSI(14) -- classic Wilder smoothing
    delta = out["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out["rsi_14"] = 100 - (100 / (1 + rs))

    # Bollinger-style z-score of price vs its 20-period mean/std
    rolling_std = out["close"].rolling(20).std()
    out["zscore_20"] = (out["close"] - out["sma_20"]) / rolling_std.replace(0, np.nan)

    return out


def _sigmoid(x: float) -> float:
    return 1 / (1 + np.exp(-x))


class ProbabilityEngine:
    """Blends a mean-reversion signal (z-score extremes -> revert) with a
    momentum signal (SMA20 vs SMA50 crossover + RSI confirmation) into a
    single bounded probability + signed edge."""

    def __init__(
        self,
        zscore_weight: float = 1.0,
        momentum_weight: float = 1.0,
        rsi_weight: float = 0.5,
    ):
        self.zscore_weight = zscore_weight
        self.momentum_weight = momentum_weight
        self.rsi_weight = rsi_weight

    def generate_signal(self, df: pd.DataFrame) -> Signal:
        enriched = compute_indicators(df)
        latest = enriched.iloc[-1]

        if pd.isna(latest["sma_50"]) or pd.isna(latest["zscore_20"]) or pd.isna(latest["rsi_14"]):
            return Signal(Action.HOLD, probability=0.5, edge=0.0, price=float(latest["close"]),
                           reasons=["insufficient history for a full indicator warm-up period"])

        reasons = []

        # Mean reversion component: extreme negative z-score => bullish revert bias
        mean_reversion_component = -np.clip(latest["zscore_20"], -3, 3) / 3
        reasons.append(f"zscore_20={latest['zscore_20']:.2f}")

        # Momentum component: SMA20 above SMA50 => bullish bias
        sma_spread_pct = (latest["sma_20"] - latest["sma_50"]) / latest["sma_50"]
        momentum_component = np.clip(sma_spread_pct * 20, -1, 1)
        reasons.append(f"sma20_vs_sma50_pct={sma_spread_pct:.4f}")

        # RSI component: >70 overbought (bearish tilt), <30 oversold (bullish tilt)
        rsi_component = np.clip((50 - latest["rsi_14"]) / 50, -1, 1)
        reasons.append(f"rsi_14={latest['rsi_14']:.1f}")

        edge = (
            self.zscore_weight * mean_reversion_component
            + self.momentum_weight * momentum_component
            + self.rsi_weight * rsi_component
        ) / (self.zscore_weight + self.momentum_weight + self.rsi_weight)
        edge = float(np.clip(edge, -1, 1))

        probability = float(_sigmoid(edge * 3))  # scale into a usable probability curve

        if edge > 0.05:
            action = Action.BUY
        elif edge < -0.05:
            action = Action.SELL
        else:
            action = Action.HOLD

        return Signal(action=action, probability=probability, edge=edge, price=float(latest["close"]), reasons=reasons)
