"""Durable performance-weighted capital routing.

The router stores strategy metrics and allocation snapshots in the same SQLite
file used by the swarm bus. Metrics are inputs, not executable orders: the
result is a reserve-aware budget that downstream risk controls may tighten
further. A strategy can never receive more than ``max_strategy_weight`` of
deployable capital, and a nonzero reserve is removed before routing.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List

_SCHEMA = """
CREATE TABLE IF NOT EXISTS strategy_metrics (
    strategy_name TEXT PRIMARY KEY,
    win_rate REAL NOT NULL,
    drawdown_pct REAL NOT NULL,
    volatility REAL NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS capital_allocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    total_equity REAL NOT NULL,
    reserve_amount REAL NOT NULL,
    deployable_capital REAL NOT NULL,
    allocations_json TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class StrategyMetrics:
    strategy_name: str
    win_rate: float
    drawdown_pct: float
    volatility: float


@dataclass(frozen=True)
class CapitalAllocation:
    strategy_name: str
    weight: float
    capital: float
    score: float


class CapitalAllocationLedger:
    """Single-writer-friendly metrics ledger backed by the swarm SQLite DB."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        with sqlite3.connect(db_path) as connection:
            connection.executescript(_SCHEMA)
            connection.commit()

    def record_metrics(self, metrics: StrategyMetrics) -> None:
        if not metrics.strategy_name:
            raise ValueError("strategy_name must not be empty")
        if not 0.0 <= metrics.win_rate <= 1.0:
            raise ValueError("win_rate must be in [0, 1]")
        if metrics.drawdown_pct < 0 or metrics.volatility < 0:
            raise ValueError("drawdown_pct and volatility must be non-negative")
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "INSERT OR REPLACE INTO strategy_metrics "
                "(strategy_name, win_rate, drawdown_pct, volatility, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    metrics.strategy_name,
                    metrics.win_rate,
                    metrics.drawdown_pct,
                    metrics.volatility,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            connection.commit()

    def metrics(self) -> List[StrategyMetrics]:
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                "SELECT strategy_name, win_rate, drawdown_pct, volatility "
                "FROM strategy_metrics ORDER BY strategy_name"
            ).fetchall()
        return [StrategyMetrics(*row) for row in rows]

    def route(
        self,
        total_equity: float,
        reserve_pct: float,
        max_strategy_weight: float = 0.50,
        available_cash: float | None = None,
        metrics: Iterable[StrategyMetrics] | None = None,
    ) -> List[CapitalAllocation]:
        if total_equity < 0:
            raise ValueError("total_equity must be non-negative")
        if available_cash is not None and available_cash < 0:
            raise ValueError("available_cash must be non-negative")
        if not 0.0 <= reserve_pct < 1.0:
            raise ValueError("reserve_pct must be in [0, 1)")
        if not 0.0 < max_strategy_weight <= 1.0:
            raise ValueError("max_strategy_weight must be in (0, 1]")

        strategy_metrics = list(metrics) if metrics is not None else self.metrics()
        if not strategy_metrics:
            return []

        # Reward wins, penalize drawdown, and penalize unstable strategies.
        scores = {
            item.strategy_name: max(0.0, item.win_rate * (1.0 - min(item.drawdown_pct, 1.0)))
            / max(item.volatility, 0.01)
            for item in strategy_metrics
        }
        total_score = sum(scores.values())
        raw_weights = (
            {name: 1.0 / len(scores) for name in scores}
            if total_score <= 0
            else {name: score / total_score for name, score in scores.items()}
        )

        # Cap outliers, then redistribute the remainder among uncapped
        # strategies. Repeat until no uncapped strategy exceeds the ceiling.
        weights = dict(raw_weights)
        while True:
            capped = {name for name, weight in weights.items() if weight > max_strategy_weight}
            if not capped:
                break
            excess = sum(weights[name] - max_strategy_weight for name in capped)
            for name in capped:
                weights[name] = max_strategy_weight
            uncapped = [name for name in weights if name not in capped]
            if not uncapped:
                break
            uncapped_total = sum(weights[name] for name in uncapped)
            if uncapped_total <= 0:
                break
            for name in uncapped:
                weights[name] += excess * weights[name] / uncapped_total

        equity_deployable = total_equity * (1.0 - reserve_pct)
        cash_deployable = (
            None if available_cash is None else max(0.0, available_cash - total_equity * reserve_pct)
        )
        deployable = equity_deployable if cash_deployable is None else min(equity_deployable, cash_deployable)
        allocations = [
            CapitalAllocation(name, weights[name], deployable * weights[name], scores[name])
            for name in weights
        ]
        self._record_snapshot(total_equity, total_equity * reserve_pct, deployable, allocations)
        return allocations

    def _record_snapshot(
        self,
        total_equity: float,
        reserve_amount: float,
        deployable: float,
        allocations: List[CapitalAllocation],
    ) -> None:
        import json

        payload = {item.strategy_name: item.capital for item in allocations}
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "INSERT INTO capital_allocations "
                "(created_at, total_equity, reserve_amount, deployable_capital, allocations_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    datetime.now(timezone.utc).isoformat(),
                    total_equity,
                    reserve_amount,
                    deployable,
                    json.dumps(payload),
                ),
            )
            connection.commit()
