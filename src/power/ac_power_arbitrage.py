"""AC power-flow arbitrage for microgrid bus distribution under constraints.

Tactical use: a shared microgrid bus feeding many 300T hardware nodes must
route a limited real-power budget to minimize total effective cost --
where "cost" is a shadow price blending battery-drain aversion and thermal
headroom -- while respecting every node's own capacity limit. This is the
same merit-order economic-dispatch structure used in real AC power markets,
solved here as a fully vectorized greedy fill.
"""

import numpy as np


class AcPowerArbitrageScheduler:
    """Solves merit-order power allocation across capacity-limited nodes."""

    def solve_dispatch(self, total_power_budget, node_capacity, node_cost):
        """Allocate a shared power budget in ascending shadow-cost order.

        Sorts nodes by cost (cheapest to serve first), then fills each
        node's capacity from the remaining budget via a cumulative-sum
        greedy fill -- the same closed-form structure as water-filling,
        applied to cost-ranked capacity instead of noise-ranked channels.

        Tactical advantage: a single vectorized sort-and-cumsum pass
        computes the exact minimum-cost power routing across an entire
        node fleet at once, with no per-node loop.
        """
        capacity = np.atleast_1d(np.asarray(node_capacity, dtype=float))
        cost = np.atleast_1d(np.asarray(node_cost, dtype=float))

        sort_order = np.argsort(cost)
        sorted_capacity = capacity[sort_order]
        cumulative_capacity = np.cumsum(sorted_capacity)

        remaining_before_node = total_power_budget - (
            cumulative_capacity - sorted_capacity
        )
        sorted_allocation = np.clip(
            remaining_before_node, 0.0, sorted_capacity
        )

        allocation = np.empty_like(sorted_allocation)
        allocation[sort_order] = sorted_allocation

        served_mask = allocation > 0.0
        shadow_price = float(np.max(cost[served_mask])) if np.any(
            served_mask
        ) else 0.0

        return {
            "allocation": allocation,
            "shadow_price": shadow_price,
            "total_allocated": float(np.sum(allocation)),
            "unmet_demand": float(
                max(total_power_budget - np.sum(allocation), 0.0)
            ),
        }
