"""Fluid strategic adaptation: turns a PatternReport into concrete
adjustments to risk sizing, the minimum-confidence bar, and stop/take
distances. Every adjustment stays within the RiskManager's existing hard
ceilings (HARD_MAX_RISK_PER_TRADE_PCT / HARD_MAX_POSITION_PCT_OF_EQUITY) --
this module can only ask for more or less risk within that envelope, it
cannot raise the envelope itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .pattern_recognition import PatternReport

# Baseline per-regime multipliers. HIGH volatility cuts risk and demands
# more confirmation (higher probability bar, wider stops to avoid getting
# stopped out by noise); LOW volatility allows modestly larger size and a
# lower bar, since whipsaw risk is lower.
_REGIME_RISK_MULTIPLIER: Dict[str, float] = {"LOW": 1.2, "NORMAL": 1.0, "HIGH": 0.5}
_REGIME_PROBABILITY_DELTA: Dict[str, float] = {"LOW": -0.02, "NORMAL": 0.0, "HIGH": 0.05}
_REGIME_STOP_MULTIPLIER: Dict[str, float] = {"LOW": 0.8, "NORMAL": 1.0, "HIGH": 1.5}
_REGIME_TAKE_PROFIT_MULTIPLIER: Dict[str, float] = {"LOW": 0.9, "NORMAL": 1.0, "HIGH": 1.3}

# Bounds so a bad regime classification or a burst of conflicting triggers
# can never push any single multiplier outside a sane band.
MIN_RISK_MULTIPLIER = 0.25
MAX_RISK_MULTIPLIER = 1.5


@dataclass(frozen=True)
class AdaptedParameters:
    risk_multiplier: float
    probability_threshold_delta: float
    stop_loss_multiplier: float
    take_profit_multiplier: float
    rationale: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "risk_multiplier": self.risk_multiplier,
            "probability_threshold_delta": self.probability_threshold_delta,
            "stop_loss_multiplier": self.stop_loss_multiplier,
            "take_profit_multiplier": self.take_profit_multiplier,
            "rationale": self.rationale,
        }


class AdaptiveStrategyController:
    def adapt(self, pattern_report: PatternReport) -> AdaptedParameters:
        regime = pattern_report.volatility_regime
        rationale = [f"volatility_regime={regime}"]

        risk_multiplier = _REGIME_RISK_MULTIPLIER.get(regime, 1.0)
        probability_delta = _REGIME_PROBABILITY_DELTA.get(regime, 0.0)
        stop_multiplier = _REGIME_STOP_MULTIPLIER.get(regime, 1.0)
        take_multiplier = _REGIME_TAKE_PROFIT_MULTIPLIER.get(regime, 1.0)

        agreement = pattern_report.agreement_ratio
        if pattern_report.net_direction != "NEUTRAL" and agreement >= 0.75:
            # Multiple markers confirming the same direction: modestly more
            # confident sizing, never above MAX_RISK_MULTIPLIER.
            risk_multiplier *= 1.15
            rationale.append(f"confirmed_trend agreement={agreement:.2f}")
        elif pattern_report.triggers and agreement < 0.5:
            # Triggers actively disagree with each other: pull risk in.
            risk_multiplier *= 0.7
            rationale.append(f"conflicting_triggers agreement={agreement:.2f}")

        risk_multiplier = max(MIN_RISK_MULTIPLIER, min(MAX_RISK_MULTIPLIER, risk_multiplier))

        return AdaptedParameters(
            risk_multiplier=risk_multiplier,
            probability_threshold_delta=probability_delta,
            stop_loss_multiplier=stop_multiplier,
            take_profit_multiplier=take_multiplier,
            rationale=rationale,
        )
