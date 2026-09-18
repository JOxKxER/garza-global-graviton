"""Cusp catastrophe early-warning for sudden non-linear swarm bifurcations.

Tactical use: some swarm/actuator failure modes (sudden consensus collapse,
aerodynamic stall) are not gradual -- they are catastrophe-theoretic jumps
between stable equilibria of a cusp potential. Continuously tracking the
discriminant of that potential's control parameters lets a controller
detect the approach to a fold boundary before the platform actually
crosses it and jumps state discontinuously.
"""

import numpy as np


class CuspCatastropheAnalyzer:
    """Evaluates cusp-catastrophe discriminant and bifurcation proximity.

    Models V(x) = x^4/4 - a*x^2/2 - b*x, whose equilibria satisfy
    x^3 - a*x - b = 0. The discriminant Delta = 27*b^2 - 4*a^3 separates
    the monostable region (Delta > 0, one equilibrium) from the bistable
    "cusp" region (Delta < 0, three equilibria) where a small parameter
    drift can trigger a discontinuous jump between stable states.
    """

    def calc_discriminant(self, control_a, control_b):
        """Evaluate Delta = 27*b^2 - 4*a^3 for arrays of control parameters.

        Tactical advantage: a single vectorized pass screens an entire
        batch of live (a, b) operating points for catastrophe risk.
        """
        a = np.atleast_1d(np.asarray(control_a, dtype=float))
        b = np.atleast_1d(np.asarray(control_b, dtype=float))
        return 27.0 * b ** 2 - 4.0 * a ** 3

    def is_bistable(self, control_a, control_b):
        """Flag operating points inside the bistable cusp region (Delta < 0).

        Tactical advantage: identifies operating points where the system
        currently has two coexisting stable states, the precondition for
        a sudden jump if parameters drift further.
        """
        return self.calc_discriminant(control_a, control_b) < 0.0

    def calc_fold_boundary_b(self, control_a):
        """Evaluate b_fold = sqrt(4*a^3/27), the fold curve for a >= 0.

        Tactical advantage: gives the exact critical b value at which the
        system is on the verge of a discontinuous jump for a given a.
        """
        a = np.atleast_1d(np.asarray(control_a, dtype=float))
        safe_a = np.clip(a, 0.0, None)
        return np.sqrt(4.0 * safe_a ** 3 / 27.0)

    def assess_bifurcation_risk(
        self, control_a, control_b, proximity_threshold=1.0
    ):
        """Evaluate discriminant, bistability, and imminent-jump risk together.

        Tactical advantage: a single call gives a controller both the
        current stability regime and an early-warning flag for operating
        points approaching the fold boundary, before a jump occurs.
        """
        discriminant = self.calc_discriminant(control_a, control_b)
        bistable = discriminant < 0.0
        near_fold = np.abs(discriminant) < proximity_threshold
        return {
            "discriminant": discriminant,
            "is_bistable": bistable,
            "imminent_bifurcation_risk": near_fold,
        }
