"""Broker execution layer.

`BrokerClient` is the abstract interface the engine talks to. Two
implementations:

  * PaperSimulationBroker -- pure in-memory simulated fills. Zero network
    calls. This is the default and what the dry run uses.
  * AlpacaBroker -- thin wrapper around `alpaca-py`. Only imported when
    actually instantiated. Credentials come exclusively from environment
    variables (see config.py) -- never hardcode API keys in source.
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

log = logging.getLogger("trading_app.execution")


@dataclass
class OrderResult:
    order_id: str
    symbol: str
    side: str
    quantity: int
    fill_price: float
    status: str


@dataclass
class Position:
    symbol: str
    quantity: int
    avg_entry_price: float


class BrokerClient(abc.ABC):
    @abc.abstractmethod
    def get_account_equity(self) -> float: ...

    @abc.abstractmethod
    def get_position(self, symbol: str) -> Optional[Position]: ...

    @abc.abstractmethod
    def submit_order(
        self,
        symbol: str,
        quantity: int,
        side: str,
        price_hint: float,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
    ) -> OrderResult: ...

    @abc.abstractmethod
    def is_market_open(self) -> bool: ...


class PaperSimulationBroker(BrokerClient):
    """Fully local, in-memory simulated broker. No network calls, no real
    money at risk -- used by the dry run and safe for unlimited experimentation."""

    def __init__(self, starting_equity: float = 100_000.0):
        self.cash = starting_equity
        self.starting_equity = starting_equity
        self.positions: Dict[str, Position] = {}
        self._order_seq = 0

    def get_account_equity(self) -> float:
        # Cash + mark-to-market of open positions at their last known entry
        # price (the dry run doesn't track live marks between iterations).
        positions_value = sum(p.quantity * p.avg_entry_price for p in self.positions.values())
        return self.cash + positions_value

    def get_position(self, symbol: str) -> Optional[Position]:
        return self.positions.get(symbol)

    def is_market_open(self) -> bool:
        return True  # simulation: always "open"

    def submit_order(
        self,
        symbol: str,
        quantity: int,
        side: str,
        price_hint: float,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
    ) -> OrderResult:
        self._order_seq += 1
        order_id = f"SIM-{self._order_seq:06d}"
        notional = quantity * price_hint

        if side.upper() == "BUY":
            if notional > self.cash:
                return OrderResult(order_id, symbol, side, 0, price_hint, "REJECTED_INSUFFICIENT_CASH")
            self.cash -= notional
            existing = self.positions.get(symbol)
            if existing:
                total_qty = existing.quantity + quantity
                existing.avg_entry_price = (
                    existing.avg_entry_price * existing.quantity + price_hint * quantity
                ) / total_qty
                existing.quantity = total_qty
            else:
                self.positions[symbol] = Position(symbol, quantity, price_hint)
        else:  # SELL
            existing = self.positions.get(symbol)
            held_qty = existing.quantity if existing else 0
            sell_qty = min(quantity, held_qty)
            if sell_qty <= 0:
                return OrderResult(order_id, symbol, side, 0, price_hint, "REJECTED_NO_POSITION")
            self.cash += sell_qty * price_hint
            existing.quantity -= sell_qty
            if existing.quantity == 0:
                del self.positions[symbol]
            quantity = sell_qty

        log.info("[PAPER] %s %s %s @ %.2f -> %s", order_id, side, symbol, price_hint, "FILLED")
        return OrderResult(order_id, symbol, side, quantity, price_hint, "FILLED")


class AlpacaBroker(BrokerClient):
    """Live/paper broker via Alpaca. Requires `alpaca-py` and
    ALPACA_API_KEY/ALPACA_SECRET_KEY. Uses ALPACA_BASE_URL to determine
    paper vs. live endpoint -- config.py defaults this to the paper endpoint
    and only allows live trading with an explicit double opt-in."""

    def __init__(self, api_key: str, secret_key: str, base_url: str):
        try:
            from alpaca.trading.client import TradingClient
        except ImportError as exc:
            raise ImportError(
                "AlpacaBroker requires the 'alpaca-py' package. Install with: pip install alpaca-py"
            ) from exc

        is_paper = "paper" in base_url
        self._client = TradingClient(api_key, secret_key, paper=is_paper)

    def get_account_equity(self) -> float:
        account = self._client.get_account()
        return float(account.equity)

    def get_position(self, symbol: str) -> Optional[Position]:
        try:
            pos = self._client.get_open_position(symbol)
            return Position(symbol, int(float(pos.qty)), float(pos.avg_entry_price))
        except Exception:
            return None

    def is_market_open(self) -> bool:
        clock = self._client.get_clock()
        return bool(clock.is_open)

    def submit_order(
        self,
        symbol: str,
        quantity: int,
        side: str,
        price_hint: float,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
    ) -> OrderResult:
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest

        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )
        order = self._client.submit_order(order_request)
        return OrderResult(
            order_id=str(order.id),
            symbol=symbol,
            side=side,
            quantity=quantity,
            fill_price=price_hint,
            status=str(order.status),
        )
