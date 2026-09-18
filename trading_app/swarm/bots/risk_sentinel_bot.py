"""Risk Sentinel Bot: the only bot with authority to approve or reject a
candidate trade. Reads settled-cash/equity snapshots that the Settlement
Ledger Bot publishes (single-writer for that state), applies Kelly sizing
and the drawdown circuit breaker, and persists the circuit breaker's
tripped flag to durable shared state -- so if this bot itself crashes and
the orchestrator restarts it, a previously-tripped breaker stays tripped
rather than silently resetting.

Also consults two optional, fluid inputs before sizing (both default to
neutral/no-op if the bots that produce them aren't registered, so this bot
works standalone exactly as before):

* per-symbol adapted parameters from StrategyAdaptationBot (risk
  multiplier, probability-threshold delta, stop/take multipliers -- driven
  by pattern/volatility regime detection).
* account-wide budgeting signals from GrowthBudgetBot (an equity-milestone
  risk multiplier, and a cash-reserve-constrained max deployable capital
  ceiling).

Both are combined with RiskManager's own Kelly sizing, which still enforces
HARD_MAX_RISK_PER_TRADE_PCT / HARD_MAX_POSITION_PCT_OF_EQUITY no matter what
these adaptive inputs ask for."""

from __future__ import annotations

from datetime import date

from ...analytics.probability_engine import Action
from ...risk.risk_manager import RiskManager
from ..bot_base import SwarmBot
from ..bus import MessageBus
from .growth_budget_bot import (
    SHARED_KEY_GUARDRAIL_PROFILE,
    SHARED_KEY_EQUITY_MILESTONE_RISK_MULTIPLIER,
    SHARED_KEY_MAX_DEPLOYABLE_CAPITAL,
)
from .signal_matrix_bot import TOPIC_SIGNAL_READY
from .strategy_adaptation_bot import shared_key_for_symbol

TOPIC_TRADE_APPROVED = "trade_approved"
TOPIC_TRADE_REJECTED = "trade_rejected"

_SHARED_KEY_CIRCUIT_BREAKER_TRIPPED = "risk.circuit_breaker_tripped"
_SHARED_KEY_ACCOUNT_EQUITY = "settlement.account_equity"

# Used when the adaptation/budgeting bots haven't published anything yet
# (e.g. at startup, or if they're not registered at all) -- these are
# exactly the values that reproduce the pre-adaptive behavior.
_DEFAULT_ADAPTED_PARAMS = {
    "risk_multiplier": 1.0,
    "probability_threshold_delta": 0.0,
    "stop_loss_multiplier": 1.0,
    "take_profit_multiplier": 1.0,
}


class RiskSentinelBot(SwarmBot):
    name = "risk_sentinel_bot"
    poll_interval_seconds = 0.5

    def __init__(
        self,
        bus_db_path: str,
        risk_manager: RiskManager,
        min_signal_probability: float,
        default_equity: float = 100_000.0,
    ):
        super().__init__(bus_db_path)
        self.risk_manager = risk_manager
        self.min_signal_probability = min_signal_probability
        self.default_equity = default_equity

    def step(self, bus: MessageBus) -> None:
        # Rehydrate the circuit breaker's tripped flag from durable shared
        # state in case this bot instance was just (re)started.
        if bus.get_shared_state(_SHARED_KEY_CIRCUIT_BREAKER_TRIPPED, False):
            self.risk_manager.circuit_breaker.tripped = True

        equity = bus.get_shared_state(_SHARED_KEY_ACCOUNT_EQUITY, self.default_equity)
        guardrail_profile = bus.get_shared_state(SHARED_KEY_GUARDRAIL_PROFILE, None)
        if guardrail_profile is not None:
            self.risk_manager.circuit_breaker.max_daily_drawdown_pct = min(
                guardrail_profile["max_daily_drawdown_pct"],
                0.05,
            )
        self.risk_manager.circuit_breaker.update(equity, today=date.today())
        bus.set_shared_state(_SHARED_KEY_CIRCUIT_BREAKER_TRIPPED, self.risk_manager.circuit_breaker.tripped)

        # Account-wide budgeting signals (equity-milestone scaling, cash
        # reserve ceiling) -- neutral defaults if GrowthBudgetBot isn't
        # running yet.
        milestone_risk_multiplier = bus.get_shared_state(SHARED_KEY_EQUITY_MILESTONE_RISK_MULTIPLIER, 1.0)
        max_deployable_capital = bus.get_shared_state(SHARED_KEY_MAX_DEPLOYABLE_CAPITAL, None)

        messages = bus.consume(TOPIC_SIGNAL_READY, consumer=self.name, limit=10)
        for message in messages:
            payload = message.payload
            symbol, action, probability, price = (
                payload["symbol"], payload["action"], payload["probability"], payload["price"],
            )

            if action == Action.HOLD.value:
                continue

            # Per-symbol adapted parameters (pattern/regime-driven) --
            # neutral defaults if StrategyAdaptationBot isn't running yet.
            adapted = bus.get_shared_state(shared_key_for_symbol(symbol), _DEFAULT_ADAPTED_PARAMS)

            effective_min_probability = self.min_signal_probability + adapted["probability_threshold_delta"]
            if probability < effective_min_probability:
                bus.publish(
                    TOPIC_TRADE_REJECTED,
                    {
                        "symbol": symbol,
                        "reason": f"probability {probability:.3f} below minimum {effective_min_probability:.3f}",
                    },
                    producer=self.name,
                )
                continue
            if self.risk_manager.circuit_breaker.tripped:
                bus.publish(
                    TOPIC_TRADE_REJECTED,
                    {"symbol": symbol, "reason": "daily drawdown circuit breaker is tripped"},
                    producer=self.name,
                )
                continue

            effective_risk_multiplier = adapted["risk_multiplier"] * milestone_risk_multiplier

            sizing = self.risk_manager.size_position(
                account_equity=equity,
                price=price,
                probability=probability,
                side=action,
                risk_multiplier=effective_risk_multiplier,
                max_deployable_capital=max_deployable_capital,
                stop_loss_multiplier=adapted["stop_loss_multiplier"],
                take_profit_multiplier=adapted["take_profit_multiplier"],
            )
            if sizing.quantity <= 0:
                bus.publish(
                    TOPIC_TRADE_REJECTED, {"symbol": symbol, "reason": sizing.reason}, producer=self.name
                )
                continue

            bus.publish(
                TOPIC_TRADE_APPROVED,
                {
                    "symbol": symbol,
                    "action": action,
                    "quantity": sizing.quantity,
                    "price": price,
                    "stop_loss_price": sizing.stop_loss_price,
                    "take_profit_price": sizing.take_profit_price,
                },
                producer=self.name,
            )
