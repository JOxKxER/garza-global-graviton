"""TradeAssist paper-trading portfolio engine.

Localized simulation: virtual cash, open positions, and running P&L,
persisted to a SQLite database (Write-Ahead Logging enabled) so the
simulation history survives between app launches.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "tradeassist_paper.db"

STARTING_CASH = 100.0

_SCHEMA = """
CREATE TABLE IF NOT EXISTS portfolio_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    cash REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS positions (
    symbol TEXT PRIMARY KEY,
    quantity REAL NOT NULL,
    avg_entry_price REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    value REAL NOT NULL,
    cash_after REAL NOT NULL
);
"""


class Portfolio:
    """Cash + positions + trade history, backed by SQLite (WAL mode)."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = Path(db_path)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.executescript(_SCHEMA)
        row = self._conn.execute("SELECT cash FROM portfolio_state WHERE id = 1").fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO portfolio_state (id, cash) VALUES (1, ?)", (STARTING_CASH,)
            )
            self._conn.commit()

    # ------------------------------------------------------------- state
    @property
    def cash(self) -> float:
        return float(self._conn.execute("SELECT cash FROM portfolio_state WHERE id = 1").fetchone()[0])

    def _set_cash(self, value: float) -> None:
        self._conn.execute("UPDATE portfolio_state SET cash = ? WHERE id = 1", (value,))

    def positions(self) -> dict[str, dict[str, float]]:
        """Open positions keyed by symbol: {symbol: {quantity, avg_entry_price}}."""
        rows = self._conn.execute(
            "SELECT symbol, quantity, avg_entry_price FROM positions ORDER BY symbol"
        ).fetchall()
        return {
            symbol: {"quantity": qty, "avg_entry_price": price}
            for symbol, qty, price in rows
        }

    def trade_history(self, limit: int = 100) -> list[dict]:
        rows = self._conn.execute(
            "SELECT timestamp, symbol, side, quantity, price, value "
            "FROM trades ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "timestamp": ts,
                "symbol": sym,
                "side": side,
                "quantity": qty,
                "price": price,
                "value": value,
            }
            for ts, sym, side, qty, price, value in rows
        ]

    # --------------------------------------------------------- valuation
    def invested_capital(self, prices: dict[str, float]) -> float:
        return sum(
            pos["quantity"] * prices.get(symbol, pos["avg_entry_price"])
            for symbol, pos in self.positions().items()
        )

    def total_value(self, prices: dict[str, float]) -> float:
        return self.cash + self.invested_capital(prices)

    def unrealized_pnl(self, prices: dict[str, float]) -> float:
        return sum(
            (prices.get(symbol, pos["avg_entry_price"]) - pos["avg_entry_price"]) * pos["quantity"]
            for symbol, pos in self.positions().items()
        )

    # --------------------------------------------------------- execution
    def _record_trade(self, symbol: str, side: str, quantity: float, price: float) -> None:
        self._conn.execute(
            "INSERT INTO trades (timestamp, symbol, side, quantity, price, value, cash_after) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                symbol,
                side,
                quantity,
                price,
                quantity * price,
                self.cash,
            ),
        )

    def buy(self, symbol: str, dollar_amount: float, price: float) -> dict:
        """Buy ``dollar_amount`` worth of ``symbol`` at ``price``.

        Returns a result dict; raises ValueError on insufficient cash.
        """
        symbol = symbol.upper()
        if dollar_amount <= 0 or price <= 0:
            raise ValueError("Amount and price must be positive.")
        if dollar_amount > self.cash:
            raise ValueError(f"Insufficient cash: need ${dollar_amount:,.2f}, have ${self.cash:,.2f}.")

        quantity = dollar_amount / price
        existing = self.positions().get(symbol)
        if existing:
            new_qty = existing["quantity"] + quantity
            new_avg = (
                existing["avg_entry_price"] * existing["quantity"] + price * quantity
            ) / new_qty
            self._conn.execute(
                "UPDATE positions SET quantity = ?, avg_entry_price = ? WHERE symbol = ?",
                (new_qty, new_avg, symbol),
            )
        else:
            self._conn.execute(
                "INSERT INTO positions (symbol, quantity, avg_entry_price) VALUES (?, ?, ?)",
                (symbol, quantity, price),
            )

        self._set_cash(self.cash - dollar_amount)
        self._record_trade(symbol, "BUY", quantity, price)
        self._conn.commit()
        return {"symbol": symbol, "quantity": quantity, "price": price, "cash_after": self.cash}

    def sell(self, symbol: str, quantity: float, price: float) -> dict:
        """Sell ``quantity`` shares of ``symbol`` at ``price``.

        Returns a result dict including realized P&L; raises ValueError on
        an insufficient position.
        """
        symbol = symbol.upper()
        if quantity <= 0 or price <= 0:
            raise ValueError("Quantity and price must be positive.")
        existing = self.positions().get(symbol)
        if not existing or existing["quantity"] < quantity - 1e-12:
            held = existing["quantity"] if existing else 0.0
            raise ValueError(f"Insufficient position: selling {quantity:,.4f}, holding {held:,.4f}.")

        proceeds = quantity * price
        realized_pnl = (price - existing["avg_entry_price"]) * quantity
        remaining = existing["quantity"] - quantity
        if remaining <= 1e-12:
            self._conn.execute("DELETE FROM positions WHERE symbol = ?", (symbol,))
        else:
            self._conn.execute(
                "UPDATE positions SET quantity = ? WHERE symbol = ?", (remaining, symbol)
            )

        self._set_cash(self.cash + proceeds)
        self._record_trade(symbol, "SELL", quantity, price)
        self._conn.commit()
        return {
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "realized_pnl": realized_pnl,
            "cash_after": self.cash,
        }

    def close(self) -> None:
        self._conn.close()
