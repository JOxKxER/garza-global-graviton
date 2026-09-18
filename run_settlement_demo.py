#!/usr/bin/env python3
"""Demonstrates the settlement-aware capital allocation pipeline:
  - T+1 settlement tracking (SELL proceeds locked until settle_time)
  - the opportunity queue staying populated while cash is locked
  - a cash-account guardrail rejecting a purchase funded by unsettled cash
  - the highest-alpha staged trade firing the instant funds unlock

Zero network calls, paper broker only.
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zlib import crc32

sys.path.insert(0, str(Path(__file__).resolve().parent))

from trading_app.config import TradingConfig
from trading_app.data.ingestion import LocalDataCache, generate_synthetic_history
from trading_app.engine import TradingEngine
from trading_app.execution.broker_client import PaperSimulationBroker


def main() -> int:
    cache_dir = Path("trading_app_cache_settlement_demo")
    if cache_dir.exists():
        shutil.rmtree(cache_dir)

    config = TradingConfig()
    config.symbols = ["AAPL", "MSFT", "SPY"]
    config.cache_dir = str(cache_dir)
    config.account_type = "cash"  # the stricter, settled-cash-only model
    config.min_signal_probability = 0.0  # demo: stage everything so the queue has candidates

    cache = LocalDataCache(config.cache_dir)
    for symbol in config.symbols:
        cache.save(symbol, generate_synthetic_history(symbol, periods=500, seed=crc32(symbol.encode())))

    broker = PaperSimulationBroker(starting_equity=50_000.0)
    engine = TradingEngine(config=config, broker=broker)

    day0 = datetime(2026, 1, 5, 9, 30)  # a Monday

    print("=" * 70)
    print(" SETTLEMENT-AWARE PIPELINE DEMO (cash account, T+1)")
    print("=" * 70)

    print(f"\n[{day0}] settled cash at start: ${engine.ledger.settled_cash:,.2f}")

    # Simulate a SELL that locks proceeds for T+1
    engine._settle_order_effects("SPY", "SELL", quantity=50, price=180.0, now=day0, as_of_date=day0.date())
    print(f"Recorded a SELL of 50 SPY @ 180.00 -> proceeds pending settlement.")
    print(f"  settled_cash={engine.ledger.settled_cash:,.2f}  unsettled={engine.ledger.unsettled_total():,.2f}")
    next_unlock = engine.ledger.next_unlock(day0)
    print(f"  projected unlock: {next_unlock.settle_time} for ${next_unlock.amount:,.2f}")

    # Stage opportunities while the extra cash is still locked
    staged = engine.scan_and_stage(now=day0)
    print(f"\nStaged {staged} opportunities while capital is partly locked "
          f"(queue size={len(engine.opportunity_queue)}).")

    # Try to execute immediately -- limited to whatever settled cash remains
    print(f"\n[{day0}] attempting execution with only settled cash available...")
    results_day0 = engine.execute_from_queue(now=day0)
    for r in results_day0:
        status = r.order.status if r.order else r.note
        print(f"  {r.symbol}: {r.signal.action.value} prob={r.signal.probability:.2f} -> {status}")

    # Advance to T+1 (next business day) -- funds should now be unlocked
    day1 = day0 + timedelta(days=1)
    buying_power_before = engine.available_buying_power(day1)
    print(f"\n[{day1}] buying power after settlement processing: ${buying_power_before:,.2f}")

    results_day1 = engine.execute_from_queue(now=day1)
    print(f"Executed {len(results_day1)} additional opportunities on T+1:")
    for r in results_day1:
        status = r.order.status if r.order else r.note
        print(f"  {r.symbol}: {r.signal.action.value} prob={r.signal.probability:.2f} -> {status}")

    print(f"\nFinal settled cash: ${engine.ledger.settled_cash:,.2f}")
    print(f"Final simulated equity: ${broker.get_account_equity():,.2f}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
