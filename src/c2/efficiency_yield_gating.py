"""Efficiency yield gating for sunk-cost-resistant tactical abort decisions.

Tactical use: an autonomous swarm should not keep committing resources to
an engagement purely because it has already invested heavily -- the
classic sunk-cost trap. Gating continuation on the marginal yield (value
still gained per unit of resource still spent) forces an abort exactly
when the engagement stops paying for itself, independent of past spend.
"""

import numpy as np

DEFAULT_MIN_YIELD = 1.0


class EfficiencyYieldGate:
    """Evaluates yield-based sunk-cost-resistant continuation decisions."""

    def __init__(self, min_yield=DEFAULT_MIN_YIELD):
        """Set the minimum acceptable yield ratio to continue an engagement."""
        self.min_yield = min_yield

    def calc_yield(self, delta_pragmatic_value, resource_cost):
        """Evaluate Yield = Delta_Pragmatic_Value / Resource_Cost.

        Tactical advantage: a single vectorized pass scores an entire
        batch of live engagements by their forward-looking payoff per unit
        of remaining resource, ignoring resources already spent.
        """
        value = np.atleast_1d(
            np.asarray(delta_pragmatic_value, dtype=float)
        )
        cost = np.atleast_1d(np.asarray(resource_cost, dtype=float))
        safe_cost = np.where(cost <= 0, 1e-9, cost)
        return value / safe_cost

    def assess_abort(self, delta_pragmatic_value, resource_cost):
        """Flag engagements whose yield has fallen below the abort floor.

        Tactical advantage: converts the raw yield score into a direct,
        automated tactical-abort trigger for an entire swarm's active
        engagement list at once.
        """
        yield_ratio = self.calc_yield(delta_pragmatic_value, resource_cost)
        should_abort = yield_ratio < self.min_yield
        return {
            "yield_ratio": yield_ratio,
            "should_abort": should_abort,
        }
