"""TradingEngine: wires ingestion -> probability engine -> risk manager ->
broker execution into one per-symbol decision cycle.

Also provides a settlement-aware capital allocation pipeline (scan_and_stage /
execute_from_queue) that keeps scanning and ranking opportunities while
capital is locked pending T+1 settlement, so the top-ranked staged trade can
fire the moment buying power frees up -- see settlement/ for the ledger,
compliance guardrails, and priority queue this builds on.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional

from .analytics.probability_engine import Action, ProbabilityEngine, Signal
from .config import TradingConfig
from .data.ingestion import LocalDataCache, load_history
from .execution.broker_client import BrokerClient, OrderResult
from .risk.risk_manager import RiskManager
from .settlement.compliance import AccountType, ComplianceGuardrails, MarginMonitor
from .settlement.ledger import SettlementLedger
from .settlement.opportunity_queue import OpportunityQueue, StagedOpportunity

log = logging.getLogger("trading_app.engine")


@dataclass
class CycleResult:
    symbol: str
    signal: Signal
    order: Optional[OrderResult]
    note: str


class TradingEngine:
    def __init__(self, config: TradingConfig, broker: BrokerClient, allow_live_fetch: bool = False):
        self.config = config
        self.broker = broker
        self.cache = LocalDataCache(config.cache_dir)
        self.probability_engine = ProbabilityEngine()
        self.risk_manager = RiskManager(
            risk_per_trade_pct=config.risk_per_trade_pct,
            kelly_fraction=config.kelly_fraction,
            stop_loss_pct=config.stop_loss_pct,
            take_profit_pct=config.take_profit_pct,
            max_daily_drawdown_pct=config.max_daily_drawdown_pct,
        )
        self.allow_live_fetch = allow_live_fetch

        # --- Settlement-aware capital allocation pipeline ---
        self.ledger = SettlementLedger(
            settled_cash=broker.get_account_equity(), settlement_days=config.settlement_days
        )
        self.compliance = ComplianceGuardrails(
            account_type=AccountType(config.account_type),
            margin_monitor=MarginMonitor(config.max_leverage, config.maintenance_margin_pct),
            pdt_equity_threshold=config.pdt_equity_threshold,
        )
        self.opportunity_queue = OpportunityQueue(max_staleness_seconds=config.opportunity_staleness_seconds)
        self._margin_used: float = 0.0
        self._position_opened_on: Dict[str, date] = {}

    def run_once(self, symbol: str) -> CycleResult:
        equity = self.broker.get_account_equity()
        self.risk_manager.circuit_breaker.update(equity)

        history = load_history(symbol, self.cache, allow_live_fetch=self.allow_live_fetch)
        signal = self.probability_engine.generate_signal(history)

        if signal.action == Action.HOLD:
            return CycleResult(symbol, signal, None, "signal is HOLD; no order placed")

        if signal.probability < self.config.min_signal_probability:
            return CycleResult(
                symbol, signal, None,
                f"probability {signal.probability:.3f} below min_signal_probability "
                f"{self.config.min_signal_probability:.3f}",
            )

        if self.risk_manager.circuit_breaker.tripped:
            return CycleResult(symbol, signal, None, "daily drawdown circuit breaker tripped; skipping")

        if not self.broker.is_market_open():
            return CycleResult(symbol, signal, None, "market is closed; skipping")

        sizing = self.risk_manager.size_position(
            account_equity=equity, price=signal.price, probability=signal.probability,
            side=signal.action.value,
        )
        if sizing.quantity <= 0:
            return CycleResult(symbol, signal, None, f"no position sized: {sizing.reason}")

        order = self.broker.submit_order(
            symbol=symbol,
            quantity=sizing.quantity,
            side=signal.action.value,
            price_hint=signal.price,
            stop_loss_price=sizing.stop_loss_price,
            take_profit_price=sizing.take_profit_price,
        )
        return CycleResult(symbol, signal, order, sizing.reason)

    def run_cycle(self, symbols: Optional[List[str]] = None) -> List[CycleResult]:
        symbols = symbols or self.config.symbols
        return [self.run_once(symbol) for symbol in symbols]

    # ------------------------------------------------------------------
    # Settlement-aware capital allocation pipeline
    # ------------------------------------------------------------------

    def available_buying_power(self, now: datetime) -> float:
        """Settles anything past its unlock time, then returns what's
        actually usable right now under the configured account-type rules:
        cash accounts get settled cash only; margin accounts get equity
        scaled by max_leverage, net of margin already in use."""
        self.ledger.process_settlements(now)
        if self.compliance.account_type == AccountType.CASH:
            return self.ledger.settled_cash
        equity = self.broker.get_account_equity()
        return max(0.0, equity * self.config.max_leverage - self._margin_used)

    def scan_and_stage(self, symbols: Optional[List[str]] = None, now: Optional[datetime] = None) -> int:
        """Keeps the probability engine scanning and ranking opportunities
        even when no buying power is currently available, so the queue is
        already populated the instant capital unlocks. Returns the number
        of new opportunities staged."""
        now = now or datetime.now()
        symbols = symbols or self.config.symbols
        equity = self.broker.get_account_equity()
        staged = 0

        for symbol in symbols:
            history = load_history(symbol, self.cache, allow_live_fetch=self.allow_live_fetch)
            signal = self.probability_engine.generate_signal(history)
            if signal.action == Action.HOLD or signal.probability < self.config.min_signal_probability:
                continue

            sizing = self.risk_manager.size_position(
                account_equity=equity, price=signal.price, probability=signal.probability,
                side=signal.action.value,
            )
            if sizing.quantity <= 0:
                continue

            self.opportunity_queue.stage(
                StagedOpportunity(
                    symbol=symbol,
                    signal=signal,
                    notional_required=sizing.quantity * signal.price,
                    staged_at=now,
                )
            )
            staged += 1
        return staged

    def execute_from_queue(self, now: Optional[datetime] = None) -> List[CycleResult]:
        """Drains the opportunity queue against currently available
        (settled/compliant) buying power, executing the highest-alpha
        affordable trade(s) first. Re-checks compliance at execution time
        -- staging does not bypass any guardrail."""
        now = now or datetime.now()
        results: List[CycleResult] = []
        as_of_date = now.date()

        equity = self.broker.get_account_equity()
        self.risk_manager.circuit_breaker.update(equity)
        if self.risk_manager.circuit_breaker.tripped:
            return results

        while True:
            buying_power = self.available_buying_power(now)
            if buying_power <= 0:
                break
            opportunity = self.opportunity_queue.pop_best_affordable(now, buying_power)
            if opportunity is None:
                break

            symbol, signal = opportunity.symbol, opportunity.signal
            notional = opportunity.notional_required
            quantity = int(notional / signal.price) if signal.price > 0 else 0
            if quantity <= 0:
                continue

            violation = self._check_compliance(symbol, signal, notional, equity, as_of_date)
            if violation:
                results.append(CycleResult(symbol, signal, None, f"compliance blocked: {violation}"))
                continue

            sizing = self.risk_manager.size_position(
                account_equity=equity, price=signal.price, probability=signal.probability, side=signal.action.value
            )
            order = self.broker.submit_order(
                symbol=symbol, quantity=quantity, side=signal.action.value, price_hint=signal.price,
                stop_loss_price=sizing.stop_loss_price, take_profit_price=sizing.take_profit_price,
            )
            self._settle_order_effects(symbol, signal.action.value, quantity, signal.price, now, as_of_date)
            results.append(CycleResult(symbol, signal, order, "executed from opportunity queue"))
            equity = self.broker.get_account_equity()

        return results

    def _check_compliance(
        self, symbol: str, signal: Signal, notional: float, equity: float, as_of_date: date
    ) -> Optional[str]:
        if signal.action == Action.BUY:
            cash_violation = self.compliance.check_buy(self.ledger, notional)
            if cash_violation:
                return cash_violation
            if self.compliance.account_type == AccountType.MARGIN:
                margin_violation = self.compliance.check_margin_trade(
                    equity, self._margin_used + notional, self._margin_used + notional
                )
                if margin_violation:
                    return margin_violation
        else:  # SELL / closing a position -- check for a same-day round trip (day trade)
            if self._position_opened_on.get(symbol) == as_of_date:
                day_trade_violation = self.compliance.check_day_trade_limit(equity, as_of_date)
                if day_trade_violation:
                    return day_trade_violation
        return None

    def _settle_order_effects(
        self, symbol: str, side: str, quantity: int, price: float, now: datetime, as_of_date: date
    ) -> None:
        notional = quantity * price
        if side == "BUY":
            if self.compliance.account_type == AccountType.CASH:
                self.ledger.spend_settled_cash(notional)
            else:
                self._margin_used += notional
            self._position_opened_on.setdefault(symbol, as_of_date)
        else:  # SELL
            if self.compliance.account_type == AccountType.CASH:
                self.ledger.record_sale_proceeds(symbol, notional, now)
            else:
                self._margin_used = max(0.0, self._margin_used - notional)
            if self._position_opened_on.get(symbol) == as_of_date:
                self.compliance.day_trade_tracker.record_day_trade(as_of_date)
            self._position_opened_on.pop(symbol, None)
