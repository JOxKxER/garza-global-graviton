from trading_app.risk.risk_manager import (
    HARD_MAX_POSITION_PCT_OF_EQUITY,
    HARD_MAX_RISK_PER_TRADE_PCT,
    RiskManager,
)


def _make_manager(**overrides):
    defaults = dict(
        risk_per_trade_pct=0.01, kelly_fraction=0.5, stop_loss_pct=0.02,
        take_profit_pct=0.04, max_daily_drawdown_pct=0.03,
    )
    defaults.update(overrides)
    return RiskManager(**defaults)


def test_hard_cap_overrides_misconfigured_risk_per_trade():
    manager = _make_manager(risk_per_trade_pct=1.0)  # a config typo meaning 100%
    assert manager.risk_per_trade_pct == HARD_MAX_RISK_PER_TRADE_PCT


def test_kelly_sizing_is_zero_for_a_coinflip_with_even_payoff():
    manager = _make_manager(stop_loss_pct=0.02, take_profit_pct=0.02)
    assert manager.kelly_sized_risk_pct(probability=0.5) == 0.0


def test_kelly_sizing_increases_with_higher_probability():
    manager = _make_manager()
    low = manager.kelly_sized_risk_pct(probability=0.55)
    high = manager.kelly_sized_risk_pct(probability=0.9)
    assert 0 <= low <= high


def test_position_size_never_exceeds_hard_notional_cap():
    manager = _make_manager(risk_per_trade_pct=0.05)
    result = manager.size_position(account_equity=100_000, price=10.0, probability=0.99, side="BUY")
    max_notional = 100_000 * HARD_MAX_POSITION_PCT_OF_EQUITY
    assert result.quantity * 10.0 <= max_notional + 1e-6


def test_position_size_zero_when_circuit_breaker_tripped():
    manager = _make_manager()
    manager.circuit_breaker.reset_for_new_day(starting_equity=100_000)
    manager.circuit_breaker.update(current_equity=100_000 * (1 - manager.circuit_breaker.max_daily_drawdown_pct - 0.01))
    assert manager.circuit_breaker.tripped
    result = manager.size_position(account_equity=90_000, price=100.0, probability=0.9, side="BUY")
    assert result.quantity == 0
    assert "circuit breaker" in result.reason


def test_stop_and_take_profit_prices_for_buy_and_sell():
    manager = _make_manager(stop_loss_pct=0.02, take_profit_pct=0.04)
    buy = manager.size_position(account_equity=100_000, price=100.0, probability=0.9, side="BUY")
    assert buy.stop_loss_price < 100.0 < buy.take_profit_price

    sell = manager.size_position(account_equity=100_000, price=100.0, probability=0.9, side="SELL")
    assert sell.take_profit_price < 100.0 < sell.stop_loss_price


def test_drawdown_circuit_breaker_resets_on_new_day():
    manager = _make_manager()
    manager.circuit_breaker.reset_for_new_day(starting_equity=100_000)
    manager.circuit_breaker.update(current_equity=90_000)  # -10%, exceeds 3% default
    assert manager.circuit_breaker.tripped

    from datetime import date, timedelta
    tomorrow = date.today() + timedelta(days=1)
    manager.circuit_breaker.update(current_equity=90_000, today=tomorrow)
    assert not manager.circuit_breaker.tripped


def test_risk_multiplier_scales_position_size_within_hard_caps():
    manager = _make_manager()
    baseline = manager.size_position(account_equity=100_000, price=100.0, probability=0.9, side="BUY")
    boosted = manager.size_position(
        account_equity=100_000, price=100.0, probability=0.9, side="BUY", risk_multiplier=1.5
    )
    assert boosted.quantity >= baseline.quantity
    # Still bounded by the hard notional cap regardless of the multiplier.
    max_notional = 100_000 * HARD_MAX_POSITION_PCT_OF_EQUITY
    assert boosted.quantity * 100.0 <= max_notional + 1e-6


def test_risk_multiplier_cannot_bypass_hard_risk_per_trade_cap():
    manager = _make_manager(risk_per_trade_pct=HARD_MAX_RISK_PER_TRADE_PCT)
    huge_multiplier_pct = manager.kelly_sized_risk_pct(probability=0.99, risk_multiplier=100.0)
    assert huge_multiplier_pct <= HARD_MAX_RISK_PER_TRADE_PCT


def test_max_deployable_capital_tightens_notional_cap_further():
    manager = _make_manager(risk_per_trade_pct=0.05)
    result = manager.size_position(
        account_equity=100_000, price=10.0, probability=0.99, side="BUY", max_deployable_capital=500.0
    )
    assert result.quantity * 10.0 <= 500.0 + 1e-6


def test_stop_and_take_profit_multipliers_widen_or_tighten_distance():
    manager = _make_manager(stop_loss_pct=0.02, take_profit_pct=0.04)
    baseline = manager.size_position(account_equity=100_000, price=100.0, probability=0.9, side="BUY")
    widened = manager.size_position(
        account_equity=100_000, price=100.0, probability=0.9, side="BUY",
        stop_loss_multiplier=2.0, take_profit_multiplier=2.0,
    )
    assert widened.stop_loss_price < baseline.stop_loss_price
    assert widened.take_profit_price > baseline.take_profit_price
