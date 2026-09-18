"""Proportional Navigation (ProNav) guidance for kinetic intercept solutions.

Tactical use: computes the commanded lateral acceleration a_c = N * Vc *
lambda_dot that drives an effector onto a collision-triangle intercept with
a maneuvering target, using only the relative position/velocity between
interceptor and target -- no target maneuver model is required.
"""

import numpy as np


class ProNavGuidance:
    """Computes LOS rate, closing velocity, ProNav acceleration commands."""

    def __init__(self, navigation_gain=3.0):
        """Set the navigation gain N (typically 3-5 for ProNav)."""
        self.navigation_gain = navigation_gain

    def calc_line_of_sight_rate(self, relative_position, relative_velocity):
        """Compute lambda_dot = (r x v) / |r|^2 for arrays of intercept states.

        Tactical advantage: a single vectorized cross-product/normalize pass
        yields the LOS turn rate for an entire batch of interceptor-target
        pairs, letting an edge controller update all active engagements in
        one call instead of per-track iteration.
        """
        r = np.atleast_2d(relative_position)
        v = np.atleast_2d(relative_velocity)
        range_sq = np.sum(r * r, axis=-1)
        range_sq = np.where(range_sq == 0, 1.0, range_sq)
        cross = np.cross(r, v)
        return cross / range_sq[..., None] if cross.ndim > r.ndim - 1 else (
            cross / range_sq
        )

    def calc_closing_velocity(self, relative_position, relative_velocity):
        """Compute Vc = -(r . v) / |r|, the rate the range is closing.

        Tactical advantage: distinguishes a genuinely closing intercept
        geometry (Vc > 0) from an opening one, vectorized over all tracks.
        """
        r = np.atleast_2d(relative_position)
        v = np.atleast_2d(relative_velocity)
        range_mag = np.linalg.norm(r, axis=-1)
        range_mag = np.where(range_mag == 0, 1.0, range_mag)
        return -np.sum(r * v, axis=-1) / range_mag

    def calc_commanded_acceleration(
        self, relative_position, relative_velocity
    ):
        """Compute a_c = N * Vc * lambda_dot, the ProNav guidance command.

        Tactical advantage: the full guidance law for a batch of live
        engagements in one vectorized expression, suitable for a control
        loop running at sub-millisecond edge latency.
        """
        closing_velocity = self.calc_closing_velocity(
            relative_position, relative_velocity
        )
        los_rate = self.calc_line_of_sight_rate(
            relative_position, relative_velocity
        )
        return self.navigation_gain * closing_velocity[..., None] * los_rate
