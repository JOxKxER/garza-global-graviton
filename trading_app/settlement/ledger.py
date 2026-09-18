"""Settlement tracking ledger.

Distinguishes settled cash (usable as buying power in a cash account) from
unsettled proceeds (pending T+1 settlement) and projects the exact
timestamp each pending amount unlocks.

NOTE ON SCOPE: this models the standard US equities settlement cycle
(T+1, effective since May 2024) using simple business-day math. It does not
model holiday calendars precisely (weekends only) -- for real money, use your
broker's actual settlement date, this is a planning/compliance-education aid,
not a substitute for your broker's authoritative ledger.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List


def add_business_days(start: datetime, days: int) -> datetime:
    current = start
    remaining = days
    while remaining > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Mon-Fri
            remaining -= 1
    return current


@dataclass
class PendingSettlement:
    amount: float
    trade_time: datetime
    settle_time: datetime
    symbol: str
    note: str = ""


@dataclass
class SettlementLedger:
    settled_cash: float
    settlement_days: int = 1  # T+1 by default
    pending: List[PendingSettlement] = field(default_factory=list)

    def record_sale_proceeds(self, symbol: str, amount: float, trade_time: datetime) -> PendingSettlement:
        """Call when a SELL fills. Proceeds are NOT immediately settled cash
        -- they unlock at trade_time + settlement_days business days."""
        settle_time = add_business_days(trade_time, self.settlement_days)
        entry = PendingSettlement(amount=amount, trade_time=trade_time, settle_time=settle_time, symbol=symbol)
        self.pending.append(entry)
        return entry

    def process_settlements(self, now: datetime) -> float:
        """Moves any pending amounts whose settle_time has passed into
        settled_cash. Returns the amount newly settled this call."""
        still_pending: List[PendingSettlement] = []
        newly_settled = 0.0
        for entry in self.pending:
            if entry.settle_time <= now:
                self.settled_cash += entry.amount
                newly_settled += entry.amount
            else:
                still_pending.append(entry)
        self.pending = still_pending
        return newly_settled

    def unsettled_total(self) -> float:
        return sum(p.amount for p in self.pending)

    def next_unlock(self, now: datetime) -> PendingSettlement | None:
        """The single soonest-unlocking pending amount, or None if nothing
        is pending. Used to project exactly when buying power will increase."""
        upcoming = [p for p in self.pending if p.settle_time > now]
        if not upcoming:
            return None
        return min(upcoming, key=lambda p: p.settle_time)

    def unlock_schedule(self, now: datetime) -> List[PendingSettlement]:
        """All still-pending amounts, soonest first -- the full projection
        of when each chunk of cash becomes usable buying power."""
        return sorted((p for p in self.pending if p.settle_time > now), key=lambda p: p.settle_time)

    def spend_settled_cash(self, amount: float) -> bool:
        """Deduct from settled cash for a BUY. Returns False (and does not
        deduct) if settled cash is insufficient -- callers must check this
        rather than letting settled_cash go negative."""
        if amount > self.settled_cash:
            return False
        self.settled_cash -= amount
        return True
