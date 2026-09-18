from trading_app.risk.risk_manager import RiskManager
from trading_app.swarm.bots.risk_sentinel_bot import RiskSentinelBot, TOPIC_TRADE_APPROVED, TOPIC_TRADE_REJECTED
from trading_app.swarm.bots.signal_matrix_bot import TOPIC_SIGNAL_READY
from trading_app.swarm.bots.strategy_adaptation_bot import shared_key_for_symbol
from trading_app.swarm.bots.growth_budget_bot import (
    SHARED_KEY_EQUITY_MILESTONE_RISK_MULTIPLIER,
    SHARED_KEY_MAX_DEPLOYABLE_CAPITAL,
)
from trading_app.swarm.bus import MessageBus


def _make_manager():
    return RiskManager(
        risk_per_trade_pct=0.02, kelly_fraction=0.5, stop_loss_pct=0.02,
        take_profit_pct=0.04, max_daily_drawdown_pct=0.05,
    )


def _publish_buy_signal(bus, symbol="TST", probability=0.9, price=100.0):
    bus.publish(
        TOPIC_SIGNAL_READY,
        {"symbol": symbol, "action": "BUY", "probability": probability, "price": price},
        producer="test",
    )


def test_risk_sentinel_approves_trade_with_default_neutral_params(tmp_path):
    bus = MessageBus(str(tmp_path / "bus.db"))
    _publish_buy_signal(bus)
    bot = RiskSentinelBot(bus_db_path=bus.db_path, risk_manager=_make_manager(), min_signal_probability=0.5)
    bot.step(bus)

    approved = bus.consume(TOPIC_TRADE_APPROVED, consumer="test")
    assert len(approved) == 1


def test_risk_sentinel_rejects_when_adapted_probability_threshold_raised_above_signal(tmp_path):
    bus = MessageBus(str(tmp_path / "bus.db"))
    _publish_buy_signal(bus, probability=0.6)
    bus.set_shared_state(
        shared_key_for_symbol("TST"),
        {
            "risk_multiplier": 1.0,
            "probability_threshold_delta": 0.5,  # pushes effective bar to 1.0
            "stop_loss_multiplier": 1.0,
            "take_profit_multiplier": 1.0,
        },
    )
    bot = RiskSentinelBot(bus_db_path=bus.db_path, risk_manager=_make_manager(), min_signal_probability=0.5)
    bot.step(bus)

    rejected = bus.consume(TOPIC_TRADE_REJECTED, consumer="test")
    assert len(rejected) == 1
    assert "below minimum" in rejected[0].payload["reason"]


def test_risk_sentinel_applies_combined_risk_multiplier_from_strategy_and_budget(tmp_path):
    bus = MessageBus(str(tmp_path / "bus.db"))
    _publish_buy_signal(bus)
    bus.set_shared_state(
        shared_key_for_symbol("TST"),
        {"risk_multiplier": 1.2, "probability_threshold_delta": 0.0, "stop_loss_multiplier": 1.0, "take_profit_multiplier": 1.0},
    )
    bus.set_shared_state(SHARED_KEY_EQUITY_MILESTONE_RISK_MULTIPLIER, 1.1)

    manager_baseline = _make_manager()
    manager_boosted = _make_manager()

    bus_baseline = MessageBus(str(tmp_path / "bus_baseline.db"))
    _publish_buy_signal(bus_baseline)
    bot_baseline = RiskSentinelBot(bus_db_path=bus_baseline.db_path, risk_manager=manager_baseline, min_signal_probability=0.5)
    bot_baseline.step(bus_baseline)
    baseline_approved = bus_baseline.consume(TOPIC_TRADE_APPROVED, consumer="test")[0]

    bot_boosted = RiskSentinelBot(bus_db_path=bus.db_path, risk_manager=manager_boosted, min_signal_probability=0.5)
    bot_boosted.step(bus)
    boosted_approved = bus.consume(TOPIC_TRADE_APPROVED, consumer="test")[0]

    assert boosted_approved.payload["quantity"] >= baseline_approved.payload["quantity"]


def test_risk_sentinel_respects_max_deployable_capital_ceiling(tmp_path):
    bus = MessageBus(str(tmp_path / "bus.db"))
    _publish_buy_signal(bus, price=100.0)
    bus.set_shared_state(SHARED_KEY_MAX_DEPLOYABLE_CAPITAL, 250.0)

    bot = RiskSentinelBot(bus_db_path=bus.db_path, risk_manager=_make_manager(), min_signal_probability=0.5)
    bot.step(bus)

    approved = bus.consume(TOPIC_TRADE_APPROVED, consumer="test")
    if approved:
        assert approved[0].payload["quantity"] * 100.0 <= 250.0 + 1e-6
    else:
        rejected = bus.consume(TOPIC_TRADE_REJECTED, consumer="test")
        assert len(rejected) == 1
