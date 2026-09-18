"""Regulatory compliance guardrails: cash-account free-riding prevention,
margin maintenance/leverage limits, and Pattern Day Trader (PDT) restriction.

NOTE ON SCOPE: these are conservative, simplified implementations of real
FINRA/Reg T rules for a personal-use planning tool -- not a compliance
system reviewed by a broker-dealer's legal team. Where the real rule has
nuanced edge cases (e.g. exact free-riding timing exceptions), this module
defaults to the *stricter* interpretation rather than guessing in the
user's favor, since being overly conservative here only costs some capital
velocity, while being wrong in the permissive direction risks an actual
brokerage violation.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Deque, Optional

from .ledger import SettlementLedger


class AccountType(str, Enum):
    CASH = "cash"
    MARGIN = "margin"


class ComplianceViolation(Exception):
    """Raised (or returned as a rejection) when a proposed trade would
    breach an account-type rule. Callers must not bypass this."""


PDT_EQUITY_THRESHOLD = 25_000.0  # FINRA: below this, margin accounts are capped at 3 day trades / 5 business days
PDT_MAX_DAY_TRADES_PER_5_SESSIONS = 3
DEFAULT_MAINTENANCE_MARGIN_PCT = 0.25  # FINRA minimum; many brokers require 0.30 in-house
DEFAULT_MAX_LEVERAGE = 2.0  # standard Reg T initial margin (2:1) for a margin account


@dataclass
class DayTradeTracker:
    """Tracks round-trip (open+close same symbol same session) day trades
    over a rolling window of the last N business sessions."""

    window_sessions: int = 5
    _trade_dates: Deque[date] = field(default_factory=deque)

    def record_day_trade(self, trade_date: date) -> None:
        self._trade_dates.append(trade_date)
        self._prune(trade_date)

    def _prune(self, as_of: date) -> None:
        cutoff_sessions = sorted({d for d in self._trade_dates if d <= as_of}, reverse=True)[: self.window_sessions]
        cutoff = min(cutoff_sessions) if cutoff_sessions else as_of
        while self._trade_dates and self._trade_dates[0] < cutoff:
            self._trade_dates.popleft()

    def count_in_window(self, as_of: date) -> int:
        self._prune(as_of)
        return len(self._trade_dates)

    def would_exceed_pdt_limit(self, as_of: date) -> bool:
        return self.count_in_window(as_of) >= PDT_MAX_DAY_TRADES_PER_5_SESSIONS


@dataclass
class PositionFunding:
    """Tracks whether an open position was purchased with settled cash.
    Cash-account policy in this module: ONLY settled cash may be used to
    buy in the first place (see ComplianceGuardrails.check_buy), so every
    tracked position is, by construction, funded by settled cash -- this
    record exists so that invariant is explicit and auditable rather than
    assumed."""

    symbol: str
    funded_by_settled_cash: bool = True


class MarginMonitor:
    def __init__(
        self,
        max_leverage: float = DEFAULT_MAX_LEVERAGE,
        maintenance_margin_pct: float = DEFAULT_MAINTENANCE_MARGIN_PCT,
    ):
        self.max_leverage = max_leverage
        self.maintenance_margin_pct = maintenance_margin_pct

    def check_leverage(self, equity: float, gross_position_value_after_trade: float) -> Optional[str]:
        if equity <= 0:
            return "account equity is non-positive; no new leveraged positions permitted"
        implied_leverage = gross_position_value_after_trade / equity
        if implied_leverage > self.max_leverage:
            return (
                f"trade would bring gross leverage to {implied_leverage:.2f}x, "
                f"exceeding the configured cap of {self.max_leverage:.2f}x"
            )
        return None

    def check_maintenance_margin(self, equity: float, margin_used: float) -> Optional[str]:
        if margin_used <= 0:
            return None
        margin_pct = equity / margin_used
        if margin_pct < self.maintenance_margin_pct:
            return (
                f"maintenance margin {margin_pct:.1%} is below the required "
                f"{self.maintenance_margin_pct:.1%} -- this would trigger a margin call"
            )
        return None


class ComplianceGuardrails:
    def __init__(
        self,
        account_type: AccountType,
        margin_monitor: Optional[MarginMonitor] = None,
        pdt_equity_threshold: float = PDT_EQUITY_THRESHOLD,
    ):
        self.account_type = account_type
        self.margin_monitor = margin_monitor or MarginMonitor()
        self.pdt_equity_threshold = pdt_equity_threshold
        self.day_trade_tracker = DayTradeTracker()

    def check_buy(self, ledger: SettlementLedger, notional: float) -> Optional[str]:
        """Cash accounts: buying power is settled cash ONLY. This is the
        conservative choice that trivially prevents free-riding (using
        proceeds of an unsettled sale to fund a new purchase) rather than
        trying to model the Reg T 4(c) exceptions."""
        if self.account_type == AccountType.CASH and notional > ledger.settled_cash:
            return (
                f"cash account: order notional ${notional:,.2f} exceeds settled cash "
                f"${ledger.settled_cash:,.2f}; unsettled funds cannot be used to buy "
                f"(this is how free-riding violations are prevented)"
            )
        return None

    def check_day_trade_limit(self, equity: float, as_of: date) -> Optional[str]:
        if self.account_type != AccountType.MARGIN or equity >= self.pdt_equity_threshold:
            return None
        if self.day_trade_tracker.would_exceed_pdt_limit(as_of):
            return (
                f"PDT restriction: margin account equity ${equity:,.2f} is below "
                f"${self.pdt_equity_threshold:,.2f} and {PDT_MAX_DAY_TRADES_PER_5_SESSIONS} day "
                f"trades have already occurred in the trailing {self.day_trade_tracker.window_sessions} "
                "sessions; another day trade would trigger a PDT flag/margin call"
            )
        return None

    def check_margin_trade(
        self, equity: float, margin_used_after_trade: float, gross_position_value_after_trade: float
    ) -> Optional[str]:
        if self.account_type != AccountType.MARGIN:
            return None
        leverage_issue = self.margin_monitor.check_leverage(equity, gross_position_value_after_trade)
        if leverage_issue:
            return leverage_issue
        return self.margin_monitor.check_maintenance_margin(equity, margin_used_after_trade)
