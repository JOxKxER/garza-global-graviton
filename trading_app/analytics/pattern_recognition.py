"""Pattern Recognition & Trigger Marker engine.

Scans OHLCV history for a small set of transparent, well-known technical
markers -- Donchian channel breakouts, volume anomalies, moving-average
crossovers -- and classifies the current volatility regime. These are
standard technical-analysis heuristics, not a claim of predictive edge;
`AdaptiveStrategyController` (adaptive_strategy.py) is what turns a
PatternReport into actual parameter adjustments, and even that only ever
adjusts risk *downward or within existing hard caps* -- see risk_manager.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TriggerMarker:
    name: str
    direction: str  # "BULLISH" | "BEARISH" | "NEUTRAL"
    strength: float  # 0..1, relative confidence in this single marker


@dataclass(frozen=True)
class PatternReport:
    symbol: str
    volatility_regime: str  # "LOW" | "NORMAL" | "HIGH"
    triggers: List[TriggerMarker]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def net_direction(self) -> str:
        """Majority vote across triggers -- BULLISH/BEARISH/NEUTRAL."""
        bullish = sum(t.strength for t in self.triggers if t.direction == "BULLISH")
        bearish = sum(t.strength for t in self.triggers if t.direction == "BEARISH")
        if bullish > bearish and bullish > 0:
            return "BULLISH"
        if bearish > bullish and bearish > 0:
            return "BEARISH"
        return "NEUTRAL"

    @property
    def agreement_ratio(self) -> float:
        """0..1: how much the triggers agree with the net direction, used by
        AdaptiveStrategyController to distinguish a confirmed trend from
        conflicting/noisy signals."""
        if not self.triggers:
            return 0.0
        net = self.net_direction
        if net == "NEUTRAL":
            return 0.0
        agreeing = sum(t.strength for t in self.triggers if t.direction == net)
        total = sum(t.strength for t in self.triggers)
        return agreeing / total if total > 0 else 0.0


class PatternRecognitionEngine:
    def __init__(
        self,
        donchian_period: int = 20,
        volume_zscore_threshold: float = 2.0,
        volatility_lookback: int = 20,
        volatility_regime_history: int = 120,
    ):
        self.donchian_period = donchian_period
        self.volume_zscore_threshold = volume_zscore_threshold
        self.volatility_lookback = volatility_lookback
        self.volatility_regime_history = volatility_regime_history

    def scan(self, symbol: str, df: pd.DataFrame) -> PatternReport:
        triggers: List[TriggerMarker] = []

        if len(df) < max(self.donchian_period, 50) + 2:
            return PatternReport(symbol=symbol, volatility_regime="NORMAL", triggers=[])

        triggers.extend(self._donchian_breakout(df))
        triggers.extend(self._volume_anomaly(df))
        triggers.extend(self._moving_average_cross(df))
        regime = self._volatility_regime(df)

        return PatternReport(symbol=symbol, volatility_regime=regime, triggers=triggers)

    def _donchian_breakout(self, df: pd.DataFrame) -> List[TriggerMarker]:
        prior_high = df["high"].rolling(self.donchian_period).max().shift(1)
        prior_low = df["low"].rolling(self.donchian_period).min().shift(1)
        latest_close = df["close"].iloc[-1]

        if pd.isna(prior_high.iloc[-1]) or pd.isna(prior_low.iloc[-1]):
            return []

        if latest_close > prior_high.iloc[-1]:
            return [TriggerMarker("donchian_breakout_up", "BULLISH", strength=1.0)]
        if latest_close < prior_low.iloc[-1]:
            return [TriggerMarker("donchian_breakdown", "BEARISH", strength=1.0)]
        return []

    def _volume_anomaly(self, df: pd.DataFrame) -> List[TriggerMarker]:
        rolling_mean = df["volume"].rolling(20).mean()
        rolling_std = df["volume"].rolling(20).std()
        if pd.isna(rolling_std.iloc[-1]) or rolling_std.iloc[-1] == 0:
            return []

        zscore = (df["volume"].iloc[-1] - rolling_mean.iloc[-1]) / rolling_std.iloc[-1]
        if zscore < self.volume_zscore_threshold:
            return []

        price_change = df["close"].iloc[-1] - df["close"].iloc[-2]
        direction = "BULLISH" if price_change > 0 else "BEARISH" if price_change < 0 else "NEUTRAL"
        strength = float(min(zscore / (self.volume_zscore_threshold * 2), 1.0))
        return [TriggerMarker("volume_anomaly", direction, strength)]

    def _moving_average_cross(self, df: pd.DataFrame) -> List[TriggerMarker]:
        sma_fast = df["close"].rolling(20).mean()
        sma_slow = df["close"].rolling(50).mean()
        if len(df) < 52 or pd.isna(sma_slow.iloc[-1]) or pd.isna(sma_slow.iloc[-2]):
            return []

        was_below = sma_fast.iloc[-2] <= sma_slow.iloc[-2]
        is_above = sma_fast.iloc[-1] > sma_slow.iloc[-1]
        was_above = sma_fast.iloc[-2] >= sma_slow.iloc[-2]
        is_below = sma_fast.iloc[-1] < sma_slow.iloc[-1]

        if was_below and is_above:
            return [TriggerMarker("golden_cross", "BULLISH", strength=0.8)]
        if was_above and is_below:
            return [TriggerMarker("death_cross", "BEARISH", strength=0.8)]
        return []

    def _volatility_regime(self, df: pd.DataFrame) -> str:
        returns = df["close"].pct_change()
        realized_vol = returns.rolling(self.volatility_lookback).std()
        history = realized_vol.dropna().tail(self.volatility_regime_history)
        if len(history) < 20:
            return "NORMAL"

        current = history.iloc[-1]
        percentile = float((history <= current).mean())
        if percentile <= 0.33:
            return "LOW"
        if percentile >= 0.67:
            return "HIGH"
        return "NORMAL"
