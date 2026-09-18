import pytest

from trading_app.budgeting.equity_milestones import CashReserveManager, EquityMilestoneScaler
from trading_app.budgeting.growth_forecaster import GrowthForecaster


def test_growth_forecaster_projects_compounding_growth():
    forecaster = GrowthForecaster(expected_annual_return_pct=0.12, periods_per_year=12)
    schedule = forecaster.project(starting_equity=100_000.0, periods=12)

    assert len(schedule) == 13  # period 0 (starting point) through 12
    assert schedule[0].projected_equity == 100_000.0
    # After 12 monthly periods at a 12% annual rate, equity should have
    # grown by roughly (but not exactly, due to compounding) 12%.
    assert schedule[-1].projected_equity == pytest.approx(112_000.0, rel=0.01)
    # Monotonically increasing for a positive return rate.
    values = [p.projected_equity for p in schedule]
    assert values == sorted(values)


def test_growth_forecaster_rejects_invalid_inputs():
    forecaster = GrowthForecaster(expected_annual_return_pct=0.08)
    with pytest.raises(ValueError):
        forecaster.project(starting_equity=100_000.0, periods=-1)
    with pytest.raises(ValueError):
        GrowthForecaster(expected_annual_return_pct=0.08, periods_per_year=0)


def test_equity_milestone_scaler_scales_up_on_realized_growth():
    scaler = EquityMilestoneScaler(milestone_step_pct=0.25, risk_multiplier_step=0.10, max_risk_multiplier=2.0)
    scaler.set_baseline(100_000.0)

    state_flat = scaler.evaluate(100_000.0)
    assert state_flat.risk_multiplier == pytest.approx(1.0)

    # +55% growth -> 2 milestones reached (0.25 step) -> +0.20 multiplier
    state_grown = scaler.evaluate(155_000.0)
    assert state_grown.milestones_reached == 2
    assert state_grown.risk_multiplier == pytest.approx(1.20)


def test_equity_milestone_scaler_scales_down_on_drawdown_and_respects_floor():
    scaler = EquityMilestoneScaler(milestone_step_pct=0.25, risk_multiplier_step=0.20, min_risk_multiplier=0.5)
    scaler.set_baseline(100_000.0)

    state_drawdown = scaler.evaluate(70_000.0)  # -30% -> -1 milestone
    assert state_drawdown.milestones_reached == -1
    assert state_drawdown.risk_multiplier == pytest.approx(0.8)

    state_deep_drawdown = scaler.evaluate(10_000.0)  # deep drawdown, floor applies
    assert state_deep_drawdown.risk_multiplier == 0.5


def test_equity_milestone_scaler_never_exceeds_configured_bounds():
    scaler = EquityMilestoneScaler(max_risk_multiplier=1.5, min_risk_multiplier=0.75)
    scaler.set_baseline(100_000.0)
    state = scaler.evaluate(10_000_000.0)
    assert state.risk_multiplier == 1.5


def test_cash_reserve_manager_enforces_reserve_floor():
    manager = CashReserveManager(reserve_pct=0.10)
    deployable = manager.max_deployable_capital(equity=100_000.0, settled_cash=100_000.0)
    assert deployable == pytest.approx(90_000.0)


def test_cash_reserve_manager_never_returns_negative():
    manager = CashReserveManager(reserve_pct=0.20)
    deployable = manager.max_deployable_capital(equity=100_000.0, settled_cash=5_000.0)
    assert deployable == 0.0


def test_cash_reserve_manager_rejects_invalid_reserve_pct():
    with pytest.raises(ValueError):
        CashReserveManager(reserve_pct=1.0)
    with pytest.raises(ValueError):
        CashReserveManager(reserve_pct=-0.1)
