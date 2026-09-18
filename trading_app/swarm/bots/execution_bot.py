"""Order Execution Bot: the only bot with authority to submit an order.
`is_safe_to_restart()` returns False while an order submission is in
flight, so the orchestrator will wait rather than interrupt a broker call
mid-flight -- fault isolation must never mean "kill a bot while it might
be holding an open order request."""

from __future__ import annotations

import threading

from ...execution.broker_client import BrokerClient
from ..bot_base import SwarmBot
from ..bus import MessageBus
from .risk_sentinel_bot import TOPIC_TRADE_APPROVED

TOPIC_TRADE_EXECUTED = "trade_executed"


class ExecutionBot(SwarmBot):
    name = "execution_bot"
    poll_interval_seconds = 0.5

    def __init__(self, bus_db_path: str, broker: BrokerClient):
        super().__init__(bus_db_path)
        self.broker = broker
        self._in_flight = threading.Event()

    def is_safe_to_restart(self) -> bool:
        return not self._in_flight.is_set()

    def step(self, bus: MessageBus) -> None:
        messages = bus.consume(TOPIC_TRADE_APPROVED, consumer=self.name, limit=5)
        for message in messages:
            payload = message.payload
            self._in_flight.set()
            try:
                order = self.broker.submit_order(
                    symbol=payload["symbol"],
                    quantity=payload["quantity"],
                    side=payload["action"],
                    price_hint=payload["price"],
                    stop_loss_price=payload.get("stop_loss_price"),
                    take_profit_price=payload.get("take_profit_price"),
                )
            finally:
                self._in_flight.clear()

            bus.publish(
                TOPIC_TRADE_EXECUTED,
                {
                    "symbol": payload["symbol"],
                    "side": payload["action"],
                    "quantity": order.quantity,
                    "fill_price": order.fill_price,
                    "status": order.status,
                    "order_id": order.order_id,
                },
                producer=self.name,
            )
