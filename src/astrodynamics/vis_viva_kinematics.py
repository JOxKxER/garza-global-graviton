"""Vis-Viva orbital velocity kinematics for LEO tracking and interception.

Tactical use: gives the instantaneous orbital speed of a body at any radius
along a known orbit from a single closed-form expression, avoiding a full
numerical orbit propagation when only the current-instant intercept speed
is needed for a fire-control solution.
"""

import numpy as np

EARTH_MU_M3_S2 = 3.986004418e14


class VisVivaSolver:
    """Computes orbital speed from the Vis-Viva equation for a given orbit."""

    def __init__(self, gravitational_parameter=EARTH_MU_M3_S2):
        """Set the standard gravitational parameter GM of the central body."""
        self.gravitational_parameter = gravitational_parameter

    def calc_orbital_velocity(self, orbital_radius, semi_major_axis):
        """Evaluate v^2 = GM*(2/r - 1/a), returning speed at each radius r.

        Tactical advantage: a single vectorized expression yields the
        instantaneous speed for an entire array of tracked radii (e.g.
        along one orbit, or across a catalog of satellites) at
        sub-microsecond edge latency, with no orbit-propagation loop.
        """
        r = np.atleast_1d(np.asarray(orbital_radius, dtype=float))
        a = semi_major_axis
        velocity_sq = self.gravitational_parameter * ((2.0 / r) - (1.0 / a))
        return np.sqrt(np.clip(velocity_sq, 0.0, None))

    def calc_intercept_closing_speed(
        self, orbital_radius, semi_major_axis, interceptor_speed
    ):
        """Estimate the worst-case closing speed against a target's orbit.

        Tactical advantage: a fast upper-bound closing-speed figure for
        kinetic intercept feasibility screening, assuming a directly
        opposing interceptor course.
        """
        target_speed = self.calc_orbital_velocity(
            orbital_radius, semi_major_axis
        )
        return target_speed + interceptor_speed
