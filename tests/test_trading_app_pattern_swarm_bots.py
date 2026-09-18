from trading_app.data.ingestion import LocalDataCache, generate_synthetic_history
from trading_app.swarm.bots.data_ingestion_bot import TOPIC_MARKET_DATA_FOR_PATTERNS, TOPIC_MARKET_DATA_READY
from trading_app.swarm.bots.pattern_recognition_bot import PatternRecognitionBot, TOPIC_PATTERN_REPORT_READY
from trading_app.swarm.bots.strategy_adaptation_bot import StrategyAdaptationBot, shared_key_for_symbol
from trading_app.swarm.bots.growth_budget_bot import (
    GrowthBudgetBot,
    SHARED_KEY_EQUITY_MILESTONE_RISK_MULTIPLIER,
    SHARED_KEY_MAX_DEPLOYABLE_CAPITAL,
)
from trading_app.swarm.bus import MessageBus


def test_pattern_recognition_bot_publishes_report_for_cached_symbol(tmp_path):
    bus_db = str(tmp_path / "bus.db")
    cache_dir = str(tmp_path / "cache")
    cache = LocalDataCache(cache_dir)
    cache.save("TST", generate_synthetic_history("TST", periods=200, seed=7))

    bus = MessageBus(bus_db)
    bus.publish(TOPIC_MARKET_DATA_FOR_PATTERNS, {"symbol": "TST", "latest_close": 100.0, "bar_count": 200}, producer="test")

    bot = PatternRecognitionBot(bus_db_path=bus_db, cache_dir=cache_dir)
    bot.step(bus)

    reports = bus.consume(TOPIC_PATTERN_REPORT_READY, consumer="test_consumer")
    assert len(reports) == 1
    payload = reports[0].payload
    assert payload["symbol"] == "TST"
    assert payload["volatility_regime"] in {"LOW", "NORMAL", "HIGH"}


def test_pattern_recognition_bot_does_not_consume_from_signal_matrix_topic(tmp_path):
    """Regression guard: pattern recognition must have its own topic, not
    compete with SignalMatrixBot workers for TOPIC_MARKET_DATA_READY."""
    bus_db = str(tmp_path / "bus.db")
    bus = MessageBus(bus_db)
    bus.publish(TOPIC_MARKET_DATA_READY, {"symbol": "TST", "latest_close": 1.0, "bar_count": 1}, producer="test")

    bot = PatternRecognitionBot(bus_db_path=bus_db, cache_dir=str(tmp_path / "cache"))
    bot.step(bus)

    # The message on the *other* topic must remain unclaimed.
    assert bus.pending_count(TOPIC_MARKET_DATA_READY) == 1


def test_strategy_adaptation_bot_publishes_adapted_params_to_shared_state(tmp_path):
    bus_db = str(tmp_path / "bus.db")
    bus = MessageBus(bus_db)
    bus.publish(
        TOPIC_PATTERN_REPORT_READY,
        {
            "symbol": "TST",
            "volatility_regime": "HIGH",
            "net_direction": "NEUTRAL",
            "agreement_ratio": 0.0,
            "triggers": [],
        },
        producer="test",
    )

    bot = StrategyAdaptationBot(bus_db_path=bus_db)
    bot.step(bus)

    adapted = bus.get_shared_state(shared_key_for_symbol("TST"))
    assert adapted is not None
    assert adapted["risk_multiplier"] < 1.0  # HIGH volatility regime dampens risk


def test_growth_budget_bot_publishes_milestone_multiplier_and_deployable_cap(tmp_path):
    bus_db = str(tmp_path / "bus.db")
    bus = MessageBus(bus_db)
    bus.set_shared_state("settlement.account_equity", 150_000.0)
    bus.set_shared_state("settlement.settled_cash", 140_000.0)

    bot = GrowthBudgetBot(bus_db_path=bus_db)
    bot.step(bus)

    multiplier = bus.get_shared_state(SHARED_KEY_EQUITY_MILESTONE_RISK_MULTIPLIER)
    max_deployable = bus.get_shared_state(SHARED_KEY_MAX_DEPLOYABLE_CAPITAL)
    assert multiplier is not None
    assert max_deployable == 140_000.0 - 150_000.0 * bot.reserve_manager.reserve_pct


def test_growth_budget_bot_uses_defaults_when_no_settlement_state_yet(tmp_path):
    bus_db = str(tmp_path / "bus.db")
    bus = MessageBus(bus_db)
    bot = GrowthBudgetBot(bus_db_path=bus_db, default_equity=100_000.0, default_settled_cash=100_000.0)
    bot.step(bus)  # must not raise even with no prior shared state
    assert bus.get_shared_state(SHARED_KEY_MAX_DEPLOYABLE_CAPITAL) is not None
