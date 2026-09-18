"""Rankine-Hugoniot normal shock jump conditions for hypersonic penetration.

Tactical use: a hypersonic effector crossing a normal shock experiences a
near-discontinuous pressure/density/temperature spike as it penetrates
dense air masses; these closed-form jump ratios let onboard guidance
predict that plasma-sheath pressure spike from the free-stream Mach number
alone, without a full CFD solve.
"""

import numpy as np

DEFAULT_SPECIFIC_HEAT_RATIO = 1.4


class RankineHugoniotShock:
    """Computes normal-shock jump ratios from upstream Mach number arrays."""

    def __init__(self, specific_heat_ratio=DEFAULT_SPECIFIC_HEAT_RATIO):
        """Set the ratio of specific heats gamma (1.4 for diatomic air)."""
        self.gamma = specific_heat_ratio

    def calc_pressure_ratio(self, mach_upstream):
        """Evaluate p2/p1 = (2*gamma*M1^2 - (gamma-1)) / (gamma+1).

        Tactical advantage: vectorized over an array of live Mach numbers,
        giving the instantaneous downstream pressure spike for an entire
        trajectory profile in one call.
        """
        m1_sq = np.atleast_1d(np.asarray(mach_upstream, dtype=float)) ** 2
        numerator = 2.0 * self.gamma * m1_sq - (self.gamma - 1.0)
        return numerator / (self.gamma + 1.0)

    def calc_density_ratio(self, mach_upstream):
        """Evaluate rho2/rho1 = ((gamma+1)*M1^2) / ((gamma-1)*M1^2 + 2)."""
        m1_sq = np.atleast_1d(np.asarray(mach_upstream, dtype=float)) ** 2
        numerator = (self.gamma + 1.0) * m1_sq
        denominator = (self.gamma - 1.0) * m1_sq + 2.0
        return numerator / denominator

    def calc_downstream_mach(self, mach_upstream):
        """Evaluate M2^2 = ((gamma-1)*M1^2+2) / (2*gamma*M1^2-(gamma-1))."""
        m1_sq = np.atleast_1d(np.asarray(mach_upstream, dtype=float)) ** 2
        numerator = (self.gamma - 1.0) * m1_sq + 2.0
        denominator = 2.0 * self.gamma * m1_sq - (self.gamma - 1.0)
        return np.sqrt(numerator / denominator)

    def evaluate_shock(self, mach_upstream):
        """Evaluate the full jump-condition set for an array of Mach numbers.

        Tactical advantage: a single call returns the pressure, density,
        and downstream Mach state needed to characterize the shock layer
        an effector must survive during atmospheric penetration.
        """
        pressure_ratio = self.calc_pressure_ratio(mach_upstream)
        density_ratio = self.calc_density_ratio(mach_upstream)
        temperature_ratio = pressure_ratio / density_ratio
        downstream_mach = self.calc_downstream_mach(mach_upstream)
        return {
            "pressure_ratio": pressure_ratio,
            "density_ratio": density_ratio,
            "temperature_ratio": temperature_ratio,
            "downstream_mach": downstream_mach,
        }
