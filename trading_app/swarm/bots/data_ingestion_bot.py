"""Data Ingestion Bot: keeps each configured symbol's local price history
cache warm and announces freshness on the bus. Never publishes bulk market
data through the bus itself -- only a lightweight "data is ready" event with
the latest price, so the bus stays fast regardless of history size."""

from __future__ import annotations

from typing import List, Optional

from ...data.ingestion import LocalDataCache, load_history
from ..bot_base import SwarmBot
from ..bus import MessageBus

TOPIC_MARKET_DATA_READY = "market_data_ready"

# Consumed by PatternRecognitionBot. A *separate* topic (not just another
# subscriber on TOPIC_MARKET_DATA_READY) because bus.consume() implements
# competing-consumer semantics -- one message is claimed by exactly one
# consumer name. SignalMatrixBot workers are meant to compete for the same
# backlog (that's how horizontal scaling load-balances them); pattern
# recognition needs its own independent copy of every event instead.
TOPIC_MARKET_DATA_FOR_PATTERNS = "market_data_ready_patterns"


class DataIngestionBot(SwarmBot):
    poll_interval_seconds = 2.0

    def __init__(
        self,
        bus_db_path: str,
        symbols: List[str],
        cache_dir: str,
        allow_live_fetch: bool = False,
        broadcast_topics: Optional[List[str]] = None,
    ):
        super().__init__(bus_db_path)
        self.name = "data_ingestion_bot"
        self.symbols = symbols
        self.cache = LocalDataCache(cache_dir)
        self.allow_live_fetch = allow_live_fetch
        self._last_published_close: dict[str, float] = {}
        self.broadcast_topics = broadcast_topics or [TOPIC_MARKET_DATA_READY, TOPIC_MARKET_DATA_FOR_PATTERNS]

    def step(self, bus: MessageBus) -> None:
        for symbol in self.symbols:
            history = load_history(symbol, self.cache, allow_live_fetch=self.allow_live_fetch)
            latest_close = float(history.iloc[-1]["close"])
            # Only publish on a genuinely new price -- otherwise a static
            # cached dataset would flood the bus with identical duplicate
            # events on every poll and starve nothing but the bus itself.
            if self._last_published_close.get(symbol) == latest_close:
                continue
            self._last_published_close[symbol] = latest_close
            payload = {"symbol": symbol, "latest_close": latest_close, "bar_count": int(len(history))}
            for topic in self.broadcast_topics:
                bus.publish(topic, payload, producer=self.name)
