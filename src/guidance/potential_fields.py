"""Artificial Potential Field (APF) repulsive forces for reactive avoidance.

Tactical use: gives each drone in a swarm an instantaneous, decentralized
avoidance vector computed only from nearby obstacle ranges -- no shared map
or planner round-trip -- so a swarm can react to urban-canyon obstacles at
control-loop speed.
"""

import numpy as np

from src.utils.math_utils import pairwise_euclidean_distance

DEFAULT_INFLUENCE_RADIUS_M = 8.0
DEFAULT_REPULSIVE_GAIN = 1.0


class PotentialFieldNavigator:
    """Computes APF repulsive potentials and forces for a drone swarm."""

    def __init__(
        self,
        influence_radius=DEFAULT_INFLUENCE_RADIUS_M,
        repulsive_gain=DEFAULT_REPULSIVE_GAIN,
    ):
        """Set the obstacle influence radius rho0 and repulsive gain eta."""
        self.influence_radius = influence_radius
        self.repulsive_gain = repulsive_gain

    def calc_repulsive_potential(self, drone_positions, obstacle_positions):
        """Evaluate U_rep(x) = 0.5*eta*(1/rho - 1/rho0)^2 within rho0, else 0.

        Tactical advantage: a single vectorized pairwise-distance pass scores
        every drone against every nearby obstacle at once, with no per-pair
        Python loop even as swarm and obstacle counts scale up.
        """
        rho = self._pairwise_ranges(drone_positions, obstacle_positions)
        in_range = rho < self.influence_radius
        safe_rho = np.where(in_range, rho, self.influence_radius)
        inverse_gap = (1.0 / safe_rho) - (1.0 / self.influence_radius)
        potential = 0.5 * self.repulsive_gain * inverse_gap ** 2
        return np.where(in_range, potential, 0.0)

    def calc_repulsive_force(self, drone_positions, obstacle_positions):
        """Evaluate F_rep = -grad(U_rep), summed per drone over all obstacles.

        Tactical advantage: yields a ready-to-use avoidance acceleration
        vector per drone in one call, letting a flight controller blend it
        directly with a goal-seeking attractive force.
        """
        rho = self._pairwise_ranges(drone_positions, obstacle_positions)
        in_range = rho < self.influence_radius
        safe_rho = np.where(in_range, rho, self.influence_radius)

        inverse_gap = (1.0 / safe_rho) - (1.0 / self.influence_radius)
        magnitude = self.repulsive_gain * inverse_gap / (safe_rho ** 2)
        magnitude = np.where(in_range, magnitude, 0.0)

        direction = self._pairwise_directions(
            drone_positions, obstacle_positions, safe_rho
        )
        force_per_pair = magnitude[..., None] * direction
        return np.sum(force_per_pair, axis=1)

    def _pairwise_ranges(self, drone_positions, obstacle_positions):
        """Compute the (num_drones, num_obstacles) pairwise distance matrix."""
        return pairwise_euclidean_distance(
            drone_positions, obstacle_positions
        )

    def _pairwise_directions(self, drone_positions, obstacle_positions, rho):
        """Compute unit vectors pointing from each obstacle to each drone."""
        diff = drone_positions[:, None, :] - obstacle_positions[None, :, :]
        return diff / rho[..., None]
