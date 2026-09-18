"""Risk management: position sizing, stop-loss/take-profit, and a daily
maximum-drawdown circuit breaker. These are the hard safety rails; the
probability engine only *suggests* a direction and confidence, this module
decides whether and how much to actually risk.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

# Hard ceilings that apply NO MATTER WHAT the config or Kelly formula says.
# These exist so a config typo (e.g. RISK_PER_TRADE_PCT=1.0 meant to be 0.01)
# cannot wipe out an account in one trade.
HARD_MAX_RISK_PER_TRADE_PCT = 0.05   # never risk more than 5% of equity on one trade
HARD_MAX_POSITION_PCT_OF_EQUITY = 0.25  # never put more than 25% of equity in one symbol


@dataclass(frozen=True)
class PositionSizeResult:
    quantity: int
    risked_amount: float
    stop_loss_price: float
    take_profit_price: float
    reason: str


class DrawdownCircuitBreaker:
    """Tracks equity across a trading day; once realized/unrealized loss from
    the day's starting equity exceeds `max_daily_drawdown_pct`, `tripped`
    becomes True and stays True until `reset_for_new_day()` is called (e.g.
    at the next session's open) -- it never silently resets mid-session."""

    def __init__(self, max_daily_drawdown_pct: float):
        self.max_daily_drawdown_pct = max_daily_drawdown_pct
        self._day_start_equity: Optional[float] = None
        self._current_day: Optional[date] = None
        self.tripped: bool = False

    def update(self, current_equity: float, today: Optional[date] = None) -> bool:
        today = today or date.today()
        if self._current_day != today:
            self.reset_for_new_day(current_equity, today)

        assert self._day_start_equity is not None
        drawdown_pct = (self._day_start_equity - current_equity) / self._day_start_equity
        if drawdown_pct >= self.max_daily_drawdown_pct:
            self.tripped = True
        return self.tripped

    def reset_for_new_day(self, starting_equity: float, today: Optional[date] = None) -> None:
        self._day_start_equity = starting_equity
        self._current_day = today or date.today()
        self.tripped = False


class RiskManager:
    def __init__(
        self,
        risk_per_trade_pct: float,
        kelly_fraction: float,
        stop_loss_pct: float,
        take_profit_pct: float,
        max_daily_drawdown_pct: float,
    ):
        self.risk_per_trade_pct = min(risk_per_trade_pct, HARD_MAX_RISK_PER_TRADE_PCT)
        self.kelly_fraction = kelly_fraction
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.circuit_breaker = DrawdownCircuitBreaker(max_daily_drawdown_pct)

    def kelly_sized_risk_pct(self, probability: float, risk_multiplier: float = 1.0) -> float:
        """Fractional Kelly criterion: f* = p - (1-p)/b, using a fixed
        payoff ratio b = take_profit_pct / stop_loss_pct (i.e. the trade's
        own risk:reward ratio). Result is scaled by `kelly_fraction` (e.g.
        0.5 = half-Kelly, the common practitioner choice to reduce variance)
        and `risk_multiplier` (adaptive strategy / equity-milestone
        adjustments -- see analytics/adaptive_strategy.py and
        budgeting/equity_milestones.py), then hard-capped at
        HARD_MAX_RISK_PER_TRADE_PCT and the configured risk_per_trade_pct,
        whichever is smaller. The multiplier can never bypass either cap."""
        b = self.take_profit_pct / self.stop_loss_pct if self.stop_loss_pct else 1.0
        p = max(0.0, min(1.0, probability))
        kelly = p - (1 - p) / b
        kelly = max(0.0, kelly)  # never size a negative-edge trade
        scaled = kelly * self.kelly_fraction * max(0.0, risk_multiplier)
        return min(scaled, self.risk_per_trade_pct, HARD_MAX_RISK_PER_TRADE_PCT)

    def size_position(
        self,
        account_equity: float,
        price: float,
        probability: float,
        side: str,
        risk_multiplier: float = 1.0,
        max_deployable_capital: Optional[float] = None,
        stop_loss_multiplier: float = 1.0,
        take_profit_multiplier: float = 1.0,
    ) -> PositionSizeResult:
        if self.circuit_breaker.tripped:
            return PositionSizeResult(0, 0.0, price, price, "daily drawdown circuit breaker is tripped")

        risk_pct = self.kelly_sized_risk_pct(probability, risk_multiplier=risk_multiplier)
        if risk_pct <= 0:
            return PositionSizeResult(0, 0.0, price, price, "non-positive Kelly edge; no position sized")

        risk_amount = account_equity * risk_pct
        per_share_risk = price * self.stop_loss_pct
        quantity = int(risk_amount / per_share_risk) if per_share_risk > 0 else 0

        # Hard cap: never let the *notional* position exceed a fixed share of equity,
        # independent of the stop-distance-based sizing above. `max_deployable_capital`
        # (e.g. from CashReserveManager) can only tighten this further, never loosen it.
        max_notional = account_equity * HARD_MAX_POSITION_PCT_OF_EQUITY
        if max_deployable_capital is not None:
            max_notional = min(max_notional, max(0.0, max_deployable_capital))
        max_qty_by_notional = int(max_notional / price) if price > 0 else 0
        quantity = min(quantity, max_qty_by_notional)

        if quantity <= 0:
            return PositionSizeResult(0, 0.0, price, price, "sized quantity rounded to zero")

        # Stop/take distances can be widened or tightened (e.g. wider stops
        # in a HIGH volatility regime to avoid noise-driven stopouts), but
        # the multiplier is applied to the *distance*, never allowed to
        # invert direction or collapse to zero.
        effective_stop_pct = max(0.0001, self.stop_loss_pct * max(0.0, stop_loss_multiplier))
        effective_take_pct = max(0.0001, self.take_profit_pct * max(0.0, take_profit_multiplier))

        if side.upper() == "BUY":
            stop_loss_price = price * (1 - effective_stop_pct)
            take_profit_price = price * (1 + effective_take_pct)
        else:
            stop_loss_price = price * (1 + effective_stop_pct)
            take_profit_price = price * (1 - effective_take_pct)

        return PositionSizeResult(
            quantity=quantity,
            risked_amount=quantity * per_share_risk,
            stop_loss_price=round(stop_loss_price, 2),
            take_profit_price=round(take_profit_price, 2),
            reason=f"kelly_fraction_risk_pct={risk_pct:.4f}",
        )
