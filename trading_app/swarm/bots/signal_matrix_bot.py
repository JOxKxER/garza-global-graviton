"""Probability & Signal Matrix Bot: consumes market-data-ready events and
computes a trading signal per symbol. This is the bot the orchestrator
scales horizontally -- multiple instances (distinct `name`s) can consume
from the same topic concurrently with zero duplicate work, because
MessageBus.consume() atomically claims each message for exactly one
consumer."""

from __future__ import annotations

import time

from ...analytics.probability_engine import ProbabilityEngine
from ...data.ingestion import LocalDataCache, load_history
from ..bot_base import SwarmBot
from ..bus import MessageBus
from .data_ingestion_bot import TOPIC_MARKET_DATA_READY

TOPIC_SIGNAL_READY = "signal_ready"


class SignalMatrixBot(SwarmBot):
    poll_interval_seconds = 0.5

    def __init__(
        self, bus_db_path: str, cache_dir: str, worker_id: int = 0, simulate_processing_delay_seconds: float = 0.0
    ):
        super().__init__(bus_db_path)
        self.name = f"signal_matrix_bot_{worker_id}"
        self.cache = LocalDataCache(cache_dir)
        self.probability_engine = ProbabilityEngine()
        # Real multi-asset probability-matrix computation (correlation
        # matrices, Monte Carlo paths, etc.) costs real CPU time; this knob
        # lets a demo/test simulate that cost without needing the real thing,
        # so backlog-triggered scaling can actually be observed and tested.
        self.simulate_processing_delay_seconds = simulate_processing_delay_seconds

    def step(self, bus: MessageBus) -> None:
        messages = bus.consume(TOPIC_MARKET_DATA_READY, consumer=self.name, limit=5)
        for message in messages:
            if self.simulate_processing_delay_seconds > 0:
                time.sleep(self.simulate_processing_delay_seconds)
            symbol = message.payload["symbol"]
            history = load_history(symbol, self.cache, allow_live_fetch=False)
            signal = self.probability_engine.generate_signal(history)
            bus.publish(
                TOPIC_SIGNAL_READY,
                {
                    "symbol": symbol,
                    "action": signal.action.value,
                    "probability": signal.probability,
                    "edge": signal.edge,
                    "price": signal.price,
                    "reasons": signal.reasons,
                },
                producer=self.name,
            )
