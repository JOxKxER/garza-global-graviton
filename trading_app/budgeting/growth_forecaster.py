"""Forward-looking capital projection: models long-term compounding growth
from the current equity at a specified expected annual return. This is a
planning/visibility tool, not a forecast guarantee -- markets do not compound
smoothly, and past or assumed returns do not predict future ones. Nothing in
this module feeds back into position sizing directly; EquityMilestoneScaler
(equity_milestones.py) is what actually ties realized equity growth to risk
sizing, and only within the RiskManager's existing hard caps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ProjectionPoint:
    period_index: int
    projected_equity: float


class GrowthForecaster:
    def __init__(self, expected_annual_return_pct: float, periods_per_year: int = 12):
        if periods_per_year <= 0:
            raise ValueError("periods_per_year must be positive")
        self.expected_annual_return_pct = expected_annual_return_pct
        self.periods_per_year = periods_per_year
        self.per_period_rate = (1 + expected_annual_return_pct) ** (1 / periods_per_year) - 1

    def project(self, starting_equity: float, periods: int) -> List[ProjectionPoint]:
        if periods < 0:
            raise ValueError("periods must be non-negative")
        schedule: List[ProjectionPoint] = [ProjectionPoint(0, starting_equity)]
        equity = starting_equity
        for period_index in range(1, periods + 1):
            equity *= 1 + self.per_period_rate
            schedule.append(ProjectionPoint(period_index, equity))
        return schedule
