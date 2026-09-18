"""Lambda-CDM Friedmann operator applied to swarm cohesion/dispersion balance.

Tactical use: models a distributed swarm the way cosmology models the
universe -- local mass draws nodes together while a repulsive "expansion"
term (analogous to dark energy) pushes them apart, giving a single closed
form radius at which swarm clustering is stable rather than collapsing or
scattering.
"""

import numpy as np


class LambdaCDMController:
    """Computes Friedmann expansion rate and swarm turnaround radius."""

    def __init__(self, H0=70.0, Omega_m=0.3, Omega_Lambda=0.7, G=6.67430e-11):
        """Set the Hubble constant, density fractions, and G."""
        self.H0 = H0
        self.Omega_m = Omega_m
        self.Omega_Lambda = Omega_Lambda
        self.G = G

    def calc_friedmann_expansion(self, scale_factor_a):
        """Evaluate H(a) = H0 * sqrt(Omega_m * a^-3 + Omega_Lambda).

        Tactical advantage: gives the instantaneous swarm dispersion rate at
        a given normalized swarm "scale" a, vectorized over arrays of a.
        """
        a = scale_factor_a
        H_squared = (self.H0 ** 2) * (
            self.Omega_m * (a ** -3) + self.Omega_Lambda
        )
        return np.sqrt(H_squared)

    def calc_turnaround_radius(self, swarm_mass_M):
        """Solve r = (G*M / (H0^2 * Omega_Lambda))^(1/3), the balance point.

        Tactical advantage: gives edge nodes a closed-form maximum safe
        cluster radius, replacing an iterative N-body stability search.
        """
        numerator = self.G * swarm_mass_M
        denominator = (self.H0 ** 2) * self.Omega_Lambda
        return np.cbrt(numerator / denominator)
