"""Strategy Adaptation Bot: consumes pattern reports and publishes bounded,
per-symbol adapted risk parameters to durable shared state, where
RiskSentinelBot reads them before sizing each trade. This is the "fluid,
forward-looking" part of strategy adaptation -- parameters shift with the
market's own recent behavior (volatility regime, trigger confirmation),
not with the outcome of any single trade.
"""

from __future__ import annotations

from dataclasses import asdict

from ...analytics.adaptive_strategy import AdaptiveStrategyController
from ...analytics.pattern_recognition import PatternReport, TriggerMarker
from ..bot_base import SwarmBot
from ..bus import MessageBus
from .pattern_recognition_bot import TOPIC_PATTERN_REPORT_READY

SHARED_KEY_PREFIX_ADAPTED_PARAMS = "strategy.adapted_params."


def shared_key_for_symbol(symbol: str) -> str:
    return f"{SHARED_KEY_PREFIX_ADAPTED_PARAMS}{symbol}"


class StrategyAdaptationBot(SwarmBot):
    name = "strategy_adaptation_bot"
    poll_interval_seconds = 1.0

    def __init__(self, bus_db_path: str, controller: AdaptiveStrategyController | None = None):
        super().__init__(bus_db_path)
        self.controller = controller or AdaptiveStrategyController()

    def step(self, bus: MessageBus) -> None:
        messages = bus.consume(TOPIC_PATTERN_REPORT_READY, consumer=self.name, limit=20)
        for message in messages:
            payload = message.payload
            report = PatternReport(
                symbol=payload["symbol"],
                volatility_regime=payload["volatility_regime"],
                triggers=[TriggerMarker(**t) for t in payload["triggers"]],
            )
            adapted = self.controller.adapt(report)
            bus.set_shared_state(shared_key_for_symbol(report.symbol), asdict(adapted))
