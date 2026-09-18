"""Equity-milestone-based position size scaling and dynamic cash reserve
management.

EquityMilestoneScaler ties a *realized* growth in account equity (never a
projection) to a risk multiplier -- every step up is capped, and a drawdown
back below a milestone symmetrically steps the multiplier back down. This
multiplier is combined with (not a replacement for) the RiskManager's
existing hard ceilings: it can only ask for more or less risk within an
already-safe envelope.

CashReserveManager enforces that a configurable fraction of equity is never
deployed into new positions -- this is what "dynamically manages cash
reserves" means here: a hard, mechanically-enforced ceiling on deployable
capital, not a soft suggestion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MilestoneState:
    baseline_equity: float
    current_equity: float
    milestones_reached: int
    risk_multiplier: float


@dataclass(frozen=True)
class GuardrailProfile:
    max_daily_drawdown_pct: float
    max_leverage: float
    maintenance_margin_pct: float


class MilestoneGuardrailScaler:
    """Adapt account-level thresholds without allowing unbounded expansion."""

    def __init__(
        self,
        base_max_daily_drawdown_pct: float = 0.03,
        base_max_leverage: float = 1.0,
        base_maintenance_margin_pct: float = 0.25,
        max_daily_drawdown_pct: float = 0.05,
        max_leverage: float = 2.0,
        min_maintenance_margin_pct: float = 0.20,
    ):
        self.base_max_daily_drawdown_pct = base_max_daily_drawdown_pct
        self.base_max_leverage = base_max_leverage
        self.base_maintenance_margin_pct = base_maintenance_margin_pct
        self.max_daily_drawdown_pct = max_daily_drawdown_pct
        self.max_leverage = max_leverage
        self.min_maintenance_margin_pct = min_maintenance_margin_pct

    def profile(self, milestones_reached: int) -> GuardrailProfile:
        scale = max(0, milestones_reached)
        return GuardrailProfile(
            max_daily_drawdown_pct=min(
                self.max_daily_drawdown_pct,
                self.base_max_daily_drawdown_pct * (1.0 + 0.10 * scale),
            ),
            max_leverage=min(self.max_leverage, self.base_max_leverage + 0.10 * scale),
            maintenance_margin_pct=max(
                self.min_maintenance_margin_pct,
                self.base_maintenance_margin_pct - 0.01 * scale,
            ),
        )


class EquityMilestoneScaler:
    def __init__(
        self,
        milestone_step_pct: float = 0.25,
        risk_multiplier_step: float = 0.10,
        max_risk_multiplier: float = 2.0,
        min_risk_multiplier: float = 0.5,
    ):
        self.milestone_step_pct = milestone_step_pct
        self.risk_multiplier_step = risk_multiplier_step
        self.max_risk_multiplier = max_risk_multiplier
        self.min_risk_multiplier = min_risk_multiplier
        self._baseline_equity: Optional[float] = None

    def set_baseline(self, equity: float) -> None:
        self._baseline_equity = equity

    def evaluate(self, current_equity: float) -> MilestoneState:
        if self._baseline_equity is None:
            self.set_baseline(current_equity)
        baseline = self._baseline_equity
        assert baseline is not None

        growth_pct = (current_equity - baseline) / baseline if baseline > 0 else 0.0
        # int() truncates toward zero, which is exactly what we want for
        # both directions: +0.55 growth at a 0.25 step -> 2 milestones up;
        # -0.30 drawdown -> -1 milestone (i.e. one step below baseline risk).
        milestones = int(growth_pct / self.milestone_step_pct)

        multiplier = 1.0 + milestones * self.risk_multiplier_step
        multiplier = max(self.min_risk_multiplier, min(self.max_risk_multiplier, multiplier))

        return MilestoneState(
            baseline_equity=baseline,
            current_equity=current_equity,
            milestones_reached=milestones,
            risk_multiplier=multiplier,
        )


class CashReserveManager:
    def __init__(self, reserve_pct: float = 0.10):
        if not 0.0 <= reserve_pct < 1.0:
            raise ValueError("reserve_pct must be in [0, 1)")
        self.reserve_pct = reserve_pct

    def max_deployable_capital(self, equity: float, settled_cash: float) -> float:
        """Hard ceiling on new-position notional: never deploy the reserved
        fraction of equity, even if it's sitting in settled cash right now."""
        reserve_amount = equity * self.reserve_pct
        return max(0.0, settled_cash - reserve_amount)
