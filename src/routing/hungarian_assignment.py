"""Optimal sensor-to-target assignment via the Hungarian algorithm.

Tactical use: given a fleet of interceptors/sensors and a set of incoming
targets, the globally-optimal pairing (minimizing total intercept time or
distance) is generally not the greedy nearest-neighbor pairing. This module
builds the cost matrix from coordinates with pure numpy broadcasting and
hands the O(n^3) combinatorial optimization to a proven exact solver.
"""

import numpy as np
from scipy.optimize import linear_sum_assignment

from src.utils.math_utils import pairwise_euclidean_distance


class SensorTargetAssigner:
    """Builds Euclidean cost matrices and solves optimal assignment on them."""

    def calc_cost_matrix(self, sensor_positions, target_positions):
        """Compute the pairwise Euclidean distance cost matrix.

        Tactical advantage: a single vectorized pass scores every
        sensor/interceptor against every target, with no per-pair loop,
        regardless of fleet or target-list size.
        """
        sensors = np.asarray(sensor_positions, dtype=float)
        targets = np.asarray(target_positions, dtype=float)
        return pairwise_euclidean_distance(sensors, targets)

    def solve_optimal_assignment(self, sensor_positions, target_positions):
        """Compute the cost matrix and solve for the min-cost pairing.

        Tactical advantage: guarantees the minimum total interception time
        across the whole engagement, which a greedy nearest-target
        heuristic cannot guarantee once assignments start to conflict.
        """
        cost_matrix = self.calc_cost_matrix(sensor_positions, target_positions)
        sensor_indices, target_indices = linear_sum_assignment(cost_matrix)
        assigned_costs = cost_matrix[sensor_indices, target_indices]
        return {
            "sensor_indices": sensor_indices,
            "target_indices": target_indices,
            "assigned_costs": assigned_costs,
            "total_cost": float(np.sum(assigned_costs)),
        }
