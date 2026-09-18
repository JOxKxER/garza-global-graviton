import shutil
from datetime import datetime, timedelta
from pathlib import Path
from zlib import crc32

import pytest

from trading_app.config import TradingConfig
from trading_app.data.ingestion import LocalDataCache, generate_synthetic_history
from trading_app.engine import TradingEngine
from trading_app.execution.broker_client import PaperSimulationBroker


@pytest.fixture
def engine(tmp_path):
    config = TradingConfig()
    config.symbols = ["AAPL", "MSFT"]
    config.cache_dir = str(tmp_path / "cache")
    config.account_type = "cash"
    config.min_signal_probability = 0.0  # stage everything for test determinism

    cache = LocalDataCache(config.cache_dir)
    for symbol in config.symbols:
        cache.save(symbol, generate_synthetic_history(symbol, periods=300, seed=crc32(symbol.encode())))

    broker = PaperSimulationBroker(starting_equity=10_000.0)
    return TradingEngine(config=config, broker=broker)


def test_ledger_initialized_from_starting_equity(engine):
    assert engine.ledger.settled_cash == 10_000.0


def test_cash_account_buy_spends_settled_cash(engine):
    now = datetime(2026, 1, 5, 9, 30)
    engine.scan_and_stage(now=now)
    assert len(engine.opportunity_queue) > 0

    results = engine.execute_from_queue(now=now)
    assert len(results) > 0
    # settled cash should have dropped (assuming at least one BUY happened)
    executed_buys = [r for r in results if r.order and r.signal.action.value == "BUY"]
    if executed_buys:
        assert engine.ledger.settled_cash < 10_000.0


def test_sell_locks_proceeds_until_t_plus_1(engine):
    now = datetime(2026, 1, 5, 9, 30)
    engine._settle_order_effects("AAPL", "BUY", quantity=10, price=100.0, now=now, as_of_date=now.date())
    equity_before = engine.ledger.settled_cash

    engine._settle_order_effects("AAPL", "SELL", quantity=10, price=110.0, now=now, as_of_date=now.date())
    assert engine.ledger.settled_cash == equity_before  # proceeds not yet settled
    assert engine.ledger.unsettled_total() == 1100.0

    tomorrow = now + timedelta(days=1)
    engine.ledger.process_settlements(tomorrow)
    assert engine.ledger.settled_cash == equity_before + 1100.0


def test_available_buying_power_reflects_settlement_state(engine):
    now = datetime(2026, 1, 5, 9, 30)
    bp_before = engine.available_buying_power(now)
    assert bp_before == 10_000.0

    engine.ledger.record_sale_proceeds("AAPL", 500.0, now)
    bp_still_locked = engine.available_buying_power(now)
    assert bp_still_locked == 10_000.0  # unsettled proceeds don't count yet

    tomorrow = now + timedelta(days=1)
    bp_after = engine.available_buying_power(tomorrow)
    assert bp_after == 10_500.0
