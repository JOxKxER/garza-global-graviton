#!/usr/bin/env python3
"""Demonstrates the multi-bot swarm: 5 specialized bots communicating only
through a shared SQLite bus, dynamic scaling of the Signal Matrix Bot pool
under a synthetic high-volatility backlog, and isolated auto-restart when
one bot is forced to fail.

Paper broker only, synthetic offline data -- zero network calls, zero real
money at risk.
"""

from __future__ import annotations

import logging
import shutil
import sys
import time
from pathlib import Path
from zlib import crc32

sys.path.insert(0, str(Path(__file__).resolve().parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

from trading_app.config import TradingConfig
from trading_app.data.ingestion import LocalDataCache, generate_synthetic_history
from trading_app.execution.broker_client import PaperSimulationBroker
from trading_app.risk.risk_manager import RiskManager
from trading_app.settlement.compliance import AccountType
from trading_app.settlement.ledger import SettlementLedger
from trading_app.swarm.bots.data_ingestion_bot import DataIngestionBot
from trading_app.swarm.bots.execution_bot import ExecutionBot
from trading_app.swarm.bots.risk_sentinel_bot import RiskSentinelBot
from trading_app.swarm.bots.settlement_ledger_bot import SettlementLedgerBot
from trading_app.swarm.bots.signal_matrix_bot import SignalMatrixBot
from trading_app.swarm.bus import MessageBus
from trading_app.swarm.orchestrator import SwarmOrchestrator


def main() -> int:
    cache_dir = Path("trading_app_swarm_demo_cache")
    bus_db_path = "trading_app_swarm_demo_bus.db"
    for path in (cache_dir, Path(bus_db_path)):
        if path.is_dir():
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()

    symbols = ["AAPL", "MSFT", "SPY", "NVDA", "TSLA", "AMD", "GOOG", "AMZN", "META", "NFLX", "INTC", "ORCL"]
    cache = LocalDataCache(str(cache_dir))
    for symbol in symbols:
        cache.save(symbol, generate_synthetic_history(symbol, periods=300, seed=crc32(symbol.encode())))

    broker = PaperSimulationBroker(starting_equity=100_000.0)
    risk_manager = RiskManager(
        risk_per_trade_pct=0.01, kelly_fraction=0.5, stop_loss_pct=0.02,
        take_profit_pct=0.04, max_daily_drawdown_pct=0.03,
    )
    ledger = SettlementLedger(settled_cash=100_000.0)

    orchestrator = SwarmOrchestrator(
        bus_db_path=bus_db_path,
        signal_matrix_backlog_scale_up_threshold=3,
        signal_matrix_backlog_scale_down_threshold=0,
        min_signal_matrix_workers=1,
        max_signal_matrix_workers=4,
    )

    orchestrator.register(
        "data_ingestion_bot",
        lambda: DataIngestionBot(bus_db_path, symbols=symbols, cache_dir=str(cache_dir)),
    )
    orchestrator.register(
        "risk_sentinel_bot",
        lambda: RiskSentinelBot(bus_db_path, risk_manager=risk_manager, min_signal_probability=0.0),
    )
    orchestrator.register("execution_bot", lambda: ExecutionBot(bus_db_path, broker=broker))
    orchestrator.register(
        "settlement_ledger_bot",
        lambda: SettlementLedgerBot(bus_db_path, broker=broker, ledger=ledger, account_type=AccountType.CASH),
    )
    orchestrator.register_signal_matrix_factory(
        lambda worker_id: SignalMatrixBot(
            bus_db_path, cache_dir=str(cache_dir), worker_id=worker_id,
            simulate_processing_delay_seconds=0.4,  # simulates real multi-asset matrix compute cost
        )
    )

    print("=" * 70)
    print(" MULTI-BOT SWARM DEMO")
    print("=" * 70)

    orchestrator.start(initial_signal_matrix_workers=1)

    monitor_bus = MessageBus(bus_db_path)
    try:
        for tick in range(30):
            time.sleep(1)
            if tick == 5:
                # Simulate a burst of new market data (a "high-volatility
                # window") by appending fresh synthetic bars for every
                # symbol -- this is what should trigger the orchestrator
                # to scale the Signal Matrix Bot pool up.
                print("\n--- simulating a burst of new market data across all symbols ---")
                for symbol in symbols:
                    df = generate_synthetic_history(symbol, periods=305, seed=crc32(symbol.encode()) + tick)
                    cache.save(symbol, df)

            if tick == 8:
                # Fault injection: force the data ingestion bot to fail on
                # every step, simulating something like a malformed payload
                # or an external API timeout. It should hit its consecutive-
                # failure limit, have its thread exit, and get restarted by
                # the orchestrator -- without any other bot even noticing.
                print("\n--- injecting a simulated failure into data_ingestion_bot ---")
                handle = orchestrator._handles["data_ingestion_bot"]

                def _broken_step(bus, _orig=handle.bot.step):
                    raise RuntimeError("simulated malformed payload / API timeout")

                handle.bot.step = _broken_step

            status = orchestrator.status()
            worker_count = sum(1 for s in status if s["is_scalable_worker"])
            backlog = monitor_bus.pending_count("market_data_ready")
            ingestion_restarts = next(
                (s["restart_count"] for s in status if s["name"] == "data_ingestion_bot"), 0
            )
            print(
                f"[t={tick:02d}] signal_matrix_workers={worker_count} backlog={backlog} "
                f"data_ingestion_bot_restarts={ingestion_restarts}"
            )
    finally:
        print("\nFinal bot status:")
        for s in orchestrator.status():
            print(f"  {s['name']}: alive={s['alive']} restarts={s['restart_count']}")

        orchestrator.stop()
        print(f"\nFinal simulated equity: ${broker.get_account_equity():,.2f}")
        print(f"Final settled cash: ${ledger.settled_cash:,.2f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
