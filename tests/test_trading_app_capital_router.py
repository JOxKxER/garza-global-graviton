import pytest

from trading_app.budgeting.capital_router import (
    CapitalAllocationLedger,
    StrategyMetrics,
)
from trading_app.budgeting.equity_milestones import MilestoneGuardrailScaler


def test_router_weights_performance_and_preserves_opportunity_reserve(tmp_path):
    ledger = CapitalAllocationLedger(str(tmp_path / "swarm.db"))
    ledger.record_metrics(StrategyMetrics("steady", 0.60, 0.02, 0.15))
    ledger.record_metrics(StrategyMetrics("volatile", 0.60, 0.15, 0.40))

    allocations = ledger.route(100_000.0, reserve_pct=0.20)
    by_name = {item.strategy_name: item for item in allocations}

    assert by_name["steady"].weight > by_name["volatile"].weight
    assert sum(item.capital for item in allocations) == pytest.approx(80_000.0)
    assert ledger.metrics()[0].strategy_name == "steady"


def test_router_caps_single_strategy_weight(tmp_path):
    ledger = CapitalAllocationLedger(str(tmp_path / "swarm.db"))
    ledger.record_metrics(StrategyMetrics("dominant", 0.99, 0.0, 0.01))
    ledger.record_metrics(StrategyMetrics("other", 0.51, 0.10, 0.50))

    allocations = ledger.route(100_000.0, reserve_pct=0.10, max_strategy_weight=0.60)
    assert max(item.weight for item in allocations) <= 0.60 + 1e-9
    assert sum(item.capital for item in allocations) == pytest.approx(90_000.0)


def test_router_tightens_equity_budget_to_settled_cash(tmp_path):
    ledger = CapitalAllocationLedger(str(tmp_path / "swarm.db"))
    ledger.record_metrics(StrategyMetrics("one", 0.5, 0.0, 0.2))
    allocations = ledger.route(
        100_000.0, reserve_pct=0.10, available_cash=20_000.0, max_strategy_weight=1.0
    )
    assert sum(item.capital for item in allocations) == pytest.approx(10_000.0)


def test_router_records_allocation_snapshot_in_sqlite(tmp_path):
    ledger = CapitalAllocationLedger(str(tmp_path / "swarm.db"))
    ledger.record_metrics(StrategyMetrics("one", 0.5, 0.0, 0.2))
    ledger.route(50_000.0, reserve_pct=0.10)

    import sqlite3

    with sqlite3.connect(str(tmp_path / "swarm.db")) as connection:
        row = connection.execute(
            "SELECT total_equity, reserve_amount, deployable_capital FROM capital_allocations"
        ).fetchone()
    assert row == pytest.approx((50_000.0, 5_000.0, 45_000.0))


def test_milestone_guardrails_expand_only_within_explicit_caps():
    scaler = MilestoneGuardrailScaler(
        base_max_daily_drawdown_pct=0.03,
        base_max_leverage=1.0,
        max_daily_drawdown_pct=0.05,
        max_leverage=1.5,
    )
    base = scaler.profile(0)
    expanded = scaler.profile(10_000)

    assert expanded.max_daily_drawdown_pct == 0.05
    assert expanded.max_leverage == 1.5
    assert expanded.maintenance_margin_pct >= scaler.min_maintenance_margin_pct
    assert base.max_daily_drawdown_pct == 0.03


def test_router_rejects_invalid_reserve(tmp_path):
    ledger = CapitalAllocationLedger(str(tmp_path / "swarm.db"))
    with pytest.raises(ValueError):
        ledger.route(100.0, reserve_pct=1.0)
