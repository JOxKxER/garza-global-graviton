"""Pattern Recognition Bot: consumes its own independent copy of market-data
freshness events (TOPIC_MARKET_DATA_FOR_PATTERNS -- see data_ingestion_bot.py
for why this is a separate topic from the one SignalMatrixBot workers
compete over), runs PatternRecognitionEngine over each symbol's cached
history, and publishes a PatternReport for downstream strategy adaptation."""

from __future__ import annotations

from dataclasses import asdict

from ...analytics.pattern_recognition import PatternRecognitionEngine
from ...data.ingestion import LocalDataCache, load_history
from ..bot_base import SwarmBot
from ..bus import MessageBus
from .data_ingestion_bot import TOPIC_MARKET_DATA_FOR_PATTERNS

TOPIC_PATTERN_REPORT_READY = "pattern_report_ready"


class PatternRecognitionBot(SwarmBot):
    name = "pattern_recognition_bot"
    poll_interval_seconds = 1.0

    def __init__(self, bus_db_path: str, cache_dir: str, engine: PatternRecognitionEngine | None = None):
        super().__init__(bus_db_path)
        self.cache = LocalDataCache(cache_dir)
        self.engine = engine or PatternRecognitionEngine()

    def step(self, bus: MessageBus) -> None:
        messages = bus.consume(TOPIC_MARKET_DATA_FOR_PATTERNS, consumer=self.name, limit=20)
        for message in messages:
            symbol = message.payload["symbol"]
            history = load_history(symbol, self.cache, allow_live_fetch=False)
            report = self.engine.scan(symbol, history)

            bus.publish(
                TOPIC_PATTERN_REPORT_READY,
                {
                    "symbol": symbol,
                    "volatility_regime": report.volatility_regime,
                    "net_direction": report.net_direction,
                    "agreement_ratio": report.agreement_ratio,
                    "triggers": [asdict(t) for t in report.triggers],
                },
                producer=self.name,
            )
