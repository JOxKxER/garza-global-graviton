"""TradeAssist dashboard entry point.

A Tkinter desktop dashboard that ties together:
  - ``config.py``        -- application thresholds (position sizing)
  - ``data_ingestion.py`` -- market data fetch with offline fallback
  - ``analyzer.py``      -- position-size assessment against the threshold

Run from the tradeassist directory:

    python app.py
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import pandas as pd

from analyzer import check_position_size, get_dynamic_threshold
from config import config
from data_ingestion import fetch_market_data
from portfolio import Portfolio

TICKERS = ["AAPL", "MSFT", "SPY", "GOOGL", "AMZN", "TSLA", "NVDA", "META"]


def _scalar(value) -> float:
    """Safely extract a float from a pandas scalar/Series/DataFrame cell.

    yfinance can return multi-level columns, in which case ``df["Close"]``
    is a DataFrame and ``.iloc[-1]`` a Series instead of a scalar. Squeeze
    down until a single value remains so ``float()`` never sees a Series.
    """
    while hasattr(value, "iloc"):
        value = value.squeeze()
        if not hasattr(value, "iloc"):
            break
        value = value.iloc[0] if value.ndim else value.item()
    return float(value)


class TradeAssistApp(tk.Tk):
    """Main dashboard window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("TradeAssist Dashboard")
        self.geometry("560x780")
        self.resizable(False, True)

        self._data: pd.DataFrame | None = None
        self._last_price: float | None = None
        self.portfolio = Portfolio()

        self._build_widgets()
        self._refresh_data()

    def destroy(self) -> None:
        self.portfolio.close()
        super().destroy()

    # ------------------------------------------------------------------ UI
    def _build_widgets(self) -> None:
        pad = {"padx": 10, "pady": 6}

        # --- Ticker selection ---
        ticker_frame = ttk.LabelFrame(self, text="Market Data")
        ticker_frame.pack(fill="x", **pad)

        ttk.Label(ticker_frame, text="Ticker:").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        # Plain text entry: type any market-wide symbol by hand.
        self.ticker_entry = tk.Entry(ticker_frame, width=12)
        self.ticker_entry.insert(0, "AAPL")
        self.ticker_entry.grid(row=0, column=1, sticky="w", padx=6, pady=6)
        self.ticker_entry.bind("<Return>", lambda _e: self._refresh_data())

        self.refresh_btn = ttk.Button(ticker_frame, text="Refresh", command=self._refresh_data)
        self.refresh_btn.grid(row=0, column=2, sticky="w", padx=6, pady=6)

        # --- Metric display fields ---
        metrics_frame = ttk.LabelFrame(self, text="Latest Metrics")
        metrics_frame.pack(fill="x", **pad)

        self.metric_vars: dict[str, tk.StringVar] = {}
        metrics = ["Last Close", "Day Change %", "30d High", "30d Low", "Avg Volume", "Data Source"]
        for i, name in enumerate(metrics):
            ttk.Label(metrics_frame, text=f"{name}:").grid(row=i, column=0, sticky="w", padx=6, pady=3)
            var = tk.StringVar(value="--")
            ttk.Label(metrics_frame, textvariable=var, font=("Segoe UI", 9, "bold")).grid(
                row=i, column=1, sticky="w", padx=6, pady=3
            )
            self.metric_vars[name] = var

        # --- Position-sizing calculator ---
        calc_frame = ttk.LabelFrame(self, text="Position-Sizing Calculator")
        calc_frame.pack(fill="x", **pad)

        ttk.Label(calc_frame, text="Account equity ($):").grid(row=0, column=0, sticky="w", padx=6, pady=3)
        self.equity_var = tk.StringVar(value="100")
        ttk.Entry(calc_frame, textvariable=self.equity_var, width=12).grid(row=0, column=1, sticky="w", padx=6, pady=3)

        ttk.Label(calc_frame, text="Position size ($):").grid(row=1, column=0, sticky="w", padx=6, pady=3)
        self.position_var = tk.StringVar(value="5")
        ttk.Entry(calc_frame, textvariable=self.position_var, width=12).grid(row=1, column=1, sticky="w", padx=6, pady=3)

        ttk.Label(calc_frame, text=f"Threshold: dynamic (starts {get_dynamic_threshold(100):.0%} @ $100 equity)").grid(
            row=2, column=0, columnspan=2, sticky="w", padx=6, pady=3
        )

        self.calc_btn = ttk.Button(calc_frame, text="Evaluate", command=self._evaluate_position)
        self.calc_btn.grid(row=3, column=0, sticky="w", padx=6, pady=6)

        self.calc_result_var = tk.StringVar(value="--")
        ttk.Label(calc_frame, textvariable=self.calc_result_var, font=("Segoe UI", 9, "bold")).grid(
            row=3, column=1, sticky="w", padx=6, pady=6
        )

        # --- Paper trading execution ---
        trade_frame = ttk.LabelFrame(self, text="Paper Trade Execution")
        trade_frame.pack(fill="x", **pad)

        ttk.Label(trade_frame, text="Trade amount ($):").grid(row=0, column=0, sticky="w", padx=6, pady=3)
        self.trade_amount_var = tk.StringVar(value="5")
        ttk.Entry(trade_frame, textvariable=self.trade_amount_var, width=12).grid(
            row=0, column=1, sticky="w", padx=6, pady=3
        )

        self.buy_btn = ttk.Button(trade_frame, text="Buy", command=self._paper_buy)
        self.buy_btn.grid(row=0, column=2, sticky="w", padx=6, pady=3)
        self.sell_btn = ttk.Button(trade_frame, text="Sell", command=self._paper_sell)
        self.sell_btn.grid(row=0, column=3, sticky="w", padx=6, pady=3)

        self.trade_result_var = tk.StringVar(value="--")
        ttk.Label(trade_frame, textvariable=self.trade_result_var, font=("Segoe UI", 9, "bold")).grid(
            row=1, column=0, columnspan=4, sticky="w", padx=6, pady=3
        )

        # --- Portfolio summary ---
        summary_frame = ttk.LabelFrame(self, text="Portfolio Summary")
        summary_frame.pack(fill="x", **pad)

        self.summary_vars: dict[str, tk.StringVar] = {}
        for i, name in enumerate(["Cash", "Invested", "Total Value", "Unrealized P&L"]):
            ttk.Label(summary_frame, text=f"{name}:").grid(row=0, column=i * 2, sticky="w", padx=6, pady=3)
            var = tk.StringVar(value="--")
            ttk.Label(summary_frame, textvariable=var, font=("Segoe UI", 9, "bold")).grid(
                row=0, column=i * 2 + 1, sticky="w", padx=6, pady=3
            )
            self.summary_vars[name] = var

        self.positions_var = tk.StringVar(value="No open positions")
        ttk.Label(summary_frame, textvariable=self.positions_var, wraplength=520).grid(
            row=1, column=0, columnspan=8, sticky="w", padx=6, pady=3
        )

        # --- Trade history log ---
        history_frame = ttk.LabelFrame(self, text="Trade History")
        history_frame.pack(fill="both", expand=True, **pad)

        self.history_tree = ttk.Treeview(
            history_frame,
            columns=("time", "symbol", "side", "qty", "price", "value"),
            show="headings",
            height=8,
        )
        for col, heading, width in [
            ("time", "Time (UTC)", 150),
            ("symbol", "Symbol", 60),
            ("side", "Side", 50),
            ("qty", "Qty", 80),
            ("price", "Price", 80),
            ("value", "Value", 90),
        ]:
            self.history_tree.heading(col, text=heading)
            self.history_tree.column(col, width=width, anchor="w")
        scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        self.history_tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        scrollbar.pack(side="right", fill="y", padx=(0, 6), pady=6)

        # --- Status bar ---
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w").pack(
            fill="x", side="bottom"
        )

    # ------------------------------------------------------------- Behavior
    def _refresh_data(self) -> None:
        symbol = self.ticker_entry.get().strip().upper()
        if not symbol:
            self.status_var.set("Enter a ticker symbol")
            return
        self.ticker_entry.delete(0, tk.END)
        self.ticker_entry.insert(0, symbol)
        self.status_var.set(f"Fetching {symbol}...")
        self.update_idletasks()

        try:
            df = fetch_market_data(symbol)
        except Exception as exc:  # defensive: ingestion already has a fallback
            self.status_var.set(f"Fetch failed: {exc}")
            return

        self._data = df
        self._update_metrics(df, symbol)
        self._refresh_portfolio_view()
        self.status_var.set(f"Loaded {symbol} ({len(df)} bars)")

    def _update_metrics(self, df: pd.DataFrame, symbol: str) -> None:
        close = df["Close"].squeeze()
        last_close = _scalar(close.iloc[-1])
        prev_close = _scalar(close.iloc[-2]) if len(close) > 1 else last_close
        change_pct = ((last_close - prev_close) / prev_close) * 100 if prev_close else 0.0
        self._last_price = last_close

        self.metric_vars["Last Close"].set(f"${last_close:,.2f}")
        self.metric_vars["Day Change %"].set(f"{change_pct:+.2f}%")
        self.metric_vars["30d High"].set(f"${_scalar(df['High'].max()):,.2f}")
        self.metric_vars["30d Low"].set(f"${_scalar(df['Low'].min()):,.2f}")
        self.metric_vars["Avg Volume"].set(f"{_scalar(df['Volume'].mean()):,.0f}")
        # The offline fallback generates a deterministic 30-bar frame; real
        # yfinance responses vary in length with the requested period.
        source = "simulated (offline fallback)" if len(df) == 30 else "yfinance (live)"
        self.metric_vars["Data Source"].set(f"{symbol} via {source}")

    def _evaluate_position(self) -> None:
        try:
            equity = float(self.equity_var.get())
            position = float(self.position_var.get())
        except ValueError:
            self.calc_result_var.set("Invalid numbers")
            return
        if equity <= 0:
            self.calc_result_var.set("Equity must be > 0")
            return

        result = check_position_size(position / equity, equity)
        verdict = result["recommendation"].upper()
        self.calc_result_var.set(
            f"{result['position_fraction']:.2%} vs limit {result['threshold']:.2%} -> {verdict}"
        )

    # -------------------------------------------------------- paper trades
    def _paper_buy(self) -> None:
        if self._last_price is None:
            self.trade_result_var.set("No price data loaded")
            return
        try:
            amount = float(self.trade_amount_var.get())
        except ValueError:
            self.trade_result_var.set("Invalid amount")
            return

        # Gate the order through the dynamic position-sizing validator.
        equity = self.portfolio.total_value({})
        if equity <= 0:
            self.trade_result_var.set("Portfolio value is zero")
            return
        check = check_position_size(amount / equity, equity)
        if check["oversized"]:
            self.trade_result_var.set(
                f"BUY REJECTED: {check['position_fraction']:.2%} exceeds "
                f"dynamic limit {check['threshold']:.2%} @ ${equity:,.2f} equity"
            )
            return

        symbol = self.ticker_entry.get().strip().upper()
        try:
            result = self.portfolio.buy(symbol, amount, self._last_price)
        except ValueError as exc:
            self.trade_result_var.set(f"BUY REJECTED: {exc}")
            return
        self.trade_result_var.set(
            f"BOUGHT {result['quantity']:.6f} {symbol} @ ${result['price']:,.2f}"
        )
        self._refresh_portfolio_view()

    def _paper_sell(self) -> None:
        if self._last_price is None:
            self.trade_result_var.set("No price data loaded")
            return
        try:
            amount = float(self.trade_amount_var.get())
        except ValueError:
            self.trade_result_var.set("Invalid amount")
            return

        symbol = self.ticker_entry.get().strip().upper()
        quantity = amount / self._last_price
        try:
            result = self.portfolio.sell(symbol, quantity, self._last_price)
        except ValueError as exc:
            self.trade_result_var.set(f"SELL REJECTED: {exc}")
            return
        self.trade_result_var.set(
            f"SOLD {result['quantity']:.6f} {symbol} @ ${result['price']:,.2f} "
            f"(realized P&L: ${result['realized_pnl']:+,.2f})"
        )
        self._refresh_portfolio_view()

    # ------------------------------------------------------ portfolio view
    def _refresh_portfolio_view(self) -> None:
        symbol = self.ticker_entry.get().strip().upper()
        prices = {symbol: self._last_price} if self._last_price else {}

        cash = self.portfolio.cash
        invested = self.portfolio.invested_capital(prices)
        total = cash + invested
        pnl = self.portfolio.unrealized_pnl(prices)

        self.summary_vars["Cash"].set(f"${cash:,.2f}")
        self.summary_vars["Invested"].set(f"${invested:,.2f}")
        self.summary_vars["Total Value"].set(f"${total:,.2f}")
        self.summary_vars["Unrealized P&L"].set(f"${pnl:+,.2f}")

        positions = self.portfolio.positions()
        if positions:
            parts = [
                f"{sym}: {pos['quantity']:.6f} sh @ ${pos['avg_entry_price']:,.2f}"
                for sym, pos in positions.items()
            ]
            self.positions_var.set("Open: " + " | ".join(parts))
        else:
            self.positions_var.set("No open positions")

        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for trade in self.portfolio.trade_history():
            self.history_tree.insert(
                "",
                "end",
                values=(
                    trade["timestamp"],
                    trade["symbol"],
                    trade["side"],
                    f"{trade['quantity']:.6f}",
                    f"${trade['price']:,.2f}",
                    f"${trade['value']:,.2f}",
                ),
            )


def main() -> None:
    app = TradeAssistApp()
    app.mainloop()


if __name__ == "__main__":
    main()
