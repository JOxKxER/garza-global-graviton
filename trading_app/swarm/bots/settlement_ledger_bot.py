"""Settlement/Ledger Bot: the single authority that mutates the settlement
ledger. Consumes trade_executed events, applies T+1 settlement bookkeeping,
and publishes the current settled cash / account equity into durable shared
state so the Risk Sentinel Bot can size the next trade against real
buying power -- without ever touching the ledger object itself."""

from __future__ import annotations

from datetime import datetime, timezone

from ...execution.broker_client import BrokerClient
from ...settlement.compliance import AccountType
from ...settlement.ledger import SettlementLedger
from ..bot_base import SwarmBot
from ..bus import MessageBus
from .execution_bot import TOPIC_TRADE_EXECUTED

TOPIC_SETTLEMENT_UPDATED = "settlement_updated"

_SHARED_KEY_ACCOUNT_EQUITY = "settlement.account_equity"
_SHARED_KEY_SETTLED_CASH = "settlement.settled_cash"


class SettlementLedgerBot(SwarmBot):
    name = "settlement_ledger_bot"
    poll_interval_seconds = 1.0

    def __init__(self, bus_db_path: str, broker: BrokerClient, ledger: SettlementLedger, account_type: AccountType):
        super().__init__(bus_db_path)
        self.broker = broker
        self.ledger = ledger
        self.account_type = account_type

    def step(self, bus: MessageBus) -> None:
        now = datetime.now(timezone.utc)
        self.ledger.process_settlements(now)

        messages = bus.consume(TOPIC_TRADE_EXECUTED, consumer=self.name, limit=10)
        for message in messages:
            payload = message.payload
            if payload["status"] != "FILLED":
                continue
            notional = payload["quantity"] * payload["fill_price"]
            if payload["side"] == "BUY" and self.account_type == AccountType.CASH:
                self.ledger.spend_settled_cash(notional)
            elif payload["side"] == "SELL" and self.account_type == AccountType.CASH:
                self.ledger.record_sale_proceeds(payload["symbol"], notional, now)

        equity = self.broker.get_account_equity()
        bus.set_shared_state(_SHARED_KEY_ACCOUNT_EQUITY, equity)
        bus.set_shared_state(_SHARED_KEY_SETTLED_CASH, self.ledger.settled_cash)
        bus.publish(
            TOPIC_SETTLEMENT_UPDATED,
            {
                "account_equity": equity,
                "settled_cash": self.ledger.settled_cash,
                "unsettled_total": self.ledger.unsettled_total(),
            },
            producer=self.name,
        )
