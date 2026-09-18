"""Isaacs' equation minimax bound solver for pursuit-evasion safety margins.

Tactical use: rather than solving the full Isaacs partial differential
equation min_u max_v[grad(V).f(x,u,v)] + g = 0 online, this module evaluates
its discretized minimax term over a finite control-direction set so a swarm
controller can get a fast worst-case closing-rate bound against an
adversarial interceptor before committing to a maneuver.
"""

import numpy as np


class IsaacsMinimaxSolver:
    """Evaluates discretized minimax pursuit-evasion closing-rate bounds."""

    def __init__(self, num_control_directions=16):
        """Set the number of discretized heading directions per agent."""
        angles = np.linspace(
            0, 2 * np.pi, num_control_directions, endpoint=False
        )
        self.directions = np.stack(
            [np.cos(angles), np.sin(angles)], axis=-1
        )

    def _velocity_field(self, speed):
        """Scale the discretized unit-direction set by a scalar speed."""
        return speed * self.directions

    def evaluate_minimax_bound(
        self, relative_position, pursuer_speed, evader_speed
    ):
        """Evaluate min_u max_v[grad(V).f(x,u,v)] over discretized controls.

        grad(V) is approximated as the unit vector along the relative
        position (steepest-ascent direction of squared separation), f is the
        relative-velocity field pursuer_u - evader_v over all sampled
        direction pairs.

        Tactical advantage: gives every swarm agent a vectorized worst-case
        closing-rate bound -- the fastest an optimally adversarial
        interceptor could close range regardless of the swarm's own
        evasive control choice -- without solving the full PDE online.
        """
        r = np.atleast_2d(relative_position)
        range_mag = np.linalg.norm(r, axis=-1, keepdims=True)
        range_mag = np.where(range_mag == 0, 1.0, range_mag)
        grad_v = r / range_mag

        pursuer_field = self._velocity_field(pursuer_speed)
        evader_field = self._velocity_field(evader_speed)

        # relative_field[a, u, v, :] = pursuer_u - evader_v per agent a.
        relative_field = (
            pursuer_field[None, :, None, :]
            - evader_field[None, None, :, :]
        )
        hamiltonian = np.einsum(
            "ad,auvd->auv", grad_v, relative_field
        )

        # Evader (v) maximizes, pursuer (u) minimizes the same term.
        worst_case_over_evader = np.max(hamiltonian, axis=-1)
        return np.min(worst_case_over_evader, axis=-1)
