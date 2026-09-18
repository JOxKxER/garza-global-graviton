"""Growth Budget Bot: reads the settlement ledger's live equity/settled-cash
shared state, and publishes forward-looking budgeting signals -- a realized
equity-milestone risk multiplier and a hard cash-reserve-constrained
deployable-capital ceiling -- into durable shared state for RiskSentinelBot
to apply. Also publishes a long-horizon growth projection purely for
visibility/logging; it never feeds back into sizing (see
budgeting/growth_forecaster.py for why: projections are a planning aid, not
a guarantee that should be allowed to influence real risk-taking)."""

from __future__ import annotations

from ...budgeting.capital_router import CapitalAllocationLedger
from ...budgeting.equity_milestones import (
    CashReserveManager,
    EquityMilestoneScaler,
    MilestoneGuardrailScaler,
)
from ...budgeting.growth_forecaster import GrowthForecaster
from ..bot_base import SwarmBot
from ..bus import MessageBus

TOPIC_GROWTH_PROJECTION_UPDATED = "growth_projection_updated"

_SHARED_KEY_ACCOUNT_EQUITY = "settlement.account_equity"
_SHARED_KEY_SETTLED_CASH = "settlement.settled_cash"

SHARED_KEY_EQUITY_MILESTONE_RISK_MULTIPLIER = "budget.equity_milestone_risk_multiplier"
SHARED_KEY_MAX_DEPLOYABLE_CAPITAL = "budget.max_deployable_capital"
SHARED_KEY_GUARDRAIL_PROFILE = "budget.guardrail_profile"
SHARED_KEY_STRATEGY_ALLOCATIONS = "budget.strategy_allocations"


class GrowthBudgetBot(SwarmBot):
    name = "growth_budget_bot"
    poll_interval_seconds = 5.0

    def __init__(
        self,
        bus_db_path: str,
        default_equity: float = 100_000.0,
        default_settled_cash: float = 100_000.0,
        milestone_scaler: EquityMilestoneScaler | None = None,
        reserve_manager: CashReserveManager | None = None,
        forecaster: GrowthForecaster | None = None,
        guardrail_scaler: MilestoneGuardrailScaler | None = None,
        capital_ledger: CapitalAllocationLedger | None = None,
        projection_periods: int = 12,
    ):
        super().__init__(bus_db_path)
        self.default_equity = default_equity
        self.default_settled_cash = default_settled_cash
        self.milestone_scaler = milestone_scaler or EquityMilestoneScaler()
        self.reserve_manager = reserve_manager or CashReserveManager()
        self.forecaster = forecaster or GrowthForecaster(expected_annual_return_pct=0.08)
        self.guardrail_scaler = guardrail_scaler or MilestoneGuardrailScaler()
        self.capital_ledger = capital_ledger
        self.projection_periods = projection_periods

    def step(self, bus: MessageBus) -> None:
        equity = bus.get_shared_state(_SHARED_KEY_ACCOUNT_EQUITY, self.default_equity)
        settled_cash = bus.get_shared_state(_SHARED_KEY_SETTLED_CASH, self.default_settled_cash)

        milestone_state = self.milestone_scaler.evaluate(equity)
        bus.set_shared_state(SHARED_KEY_EQUITY_MILESTONE_RISK_MULTIPLIER, milestone_state.risk_multiplier)
        profile = self.guardrail_scaler.profile(milestone_state.milestones_reached)
        bus.set_shared_state(SHARED_KEY_GUARDRAIL_PROFILE, profile.__dict__)

        max_deployable = self.reserve_manager.max_deployable_capital(equity, settled_cash)
        bus.set_shared_state(SHARED_KEY_MAX_DEPLOYABLE_CAPITAL, max_deployable)

        if self.capital_ledger is not None:
            allocations = self.capital_ledger.route(
                total_equity=equity,
                reserve_pct=self.reserve_manager.reserve_pct,
                available_cash=settled_cash,
            )
            bus.set_shared_state(
                SHARED_KEY_STRATEGY_ALLOCATIONS,
                {item.strategy_name: item.capital for item in allocations},
            )

        projection = self.forecaster.project(equity, self.projection_periods)
        bus.publish(
            TOPIC_GROWTH_PROJECTION_UPDATED,
            {
                "current_equity": equity,
                "milestones_reached": milestone_state.milestones_reached,
                "risk_multiplier": milestone_state.risk_multiplier,
                "max_deployable_capital": max_deployable,
                "guardrail_profile": profile.__dict__,
                "projection": [p.projected_equity for p in projection],
            },
            producer=self.name,
        )
