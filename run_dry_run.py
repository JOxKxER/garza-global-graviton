#!/usr/bin/env python3
"""Dry-run entrypoint: exercises the full pipeline (data -> probability ->
risk -> execution) with synthetic offline data and the PaperSimulationBroker.
Zero network calls, zero real money at risk -- safe to run repeatedly.

Usage:
    python run_dry_run.py [--symbols AAPL,MSFT,SPY] [--iterations 5]
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path
from zlib import crc32

sys.path.insert(0, str(Path(__file__).resolve().parent))

from trading_app.config import TradingConfig
from trading_app.data.ingestion import generate_synthetic_history, LocalDataCache
from trading_app.engine import TradingEngine
from trading_app.execution.broker_client import PaperSimulationBroker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("dry_run")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the trading_app pipeline in fully offline dry-run mode.")
    parser.add_argument("--symbols", default="AAPL,MSFT,SPY", help="Comma-separated symbol list")
    parser.add_argument("--iterations", type=int, default=5, help="Number of decision cycles to run")
    parser.add_argument("--starting-equity", type=float, default=100_000.0)
    parser.add_argument("--cache-dir", default="trading_app_cache_dryrun")
    args = parser.parse_args()

    # Fresh cache dir per dry run so repeated runs don't reuse stale synthetic data.
    cache_path = Path(args.cache_dir)
    if cache_path.exists():
        shutil.rmtree(cache_path)

    config = TradingConfig()
    config.symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    config.cache_dir = args.cache_dir
    config.trading_mode = "paper"
    config.allow_live_trading = False  # dry run can never place a live order

    cache = LocalDataCache(config.cache_dir)
    for symbol in config.symbols:
        cache.save(symbol, generate_synthetic_history(symbol, periods=500, seed=crc32(symbol.encode())))

    broker = PaperSimulationBroker(starting_equity=args.starting_equity)
    engine = TradingEngine(config=config, broker=broker, allow_live_fetch=False)

    print("=" * 70)
    print(" TRADING_APP DRY RUN (paper broker, synthetic offline data)")
    print("=" * 70)
    print(f"Symbols: {', '.join(config.symbols)}")
    print(f"Starting equity: ${args.starting_equity:,.2f}\n")

    for cycle in range(1, args.iterations + 1):
        print(f"--- Cycle {cycle}/{args.iterations} ---")
        results = engine.run_cycle()
        for r in results:
            print(
                f"  {r.symbol}: signal={r.signal.action.value} "
                f"prob={r.signal.probability:.3f} edge={r.signal.edge:+.3f} "
                f"price={r.signal.price:.2f}"
            )
            if r.order:
                print(f"    -> ORDER {r.order.status}: {r.order.side} {r.order.quantity} @ {r.order.fill_price:.2f}")
            else:
                print(f"    -> no order: {r.note}")

    final_equity = broker.get_account_equity()
    print("\n" + "=" * 70)
    print(f" FINAL SIMULATED EQUITY: ${final_equity:,.2f} "
          f"({(final_equity / args.starting_equity - 1) * 100:+.2f}% vs. start)")
    print(" (synthetic data + heuristic signals -- not a performance claim)")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
