"""Jeans Instability collapse limits mapped onto autonomous swarm density.

Tactical use: maps the astrophysical Jeans criterion (a gravitationally
bound gas cloud region collapses once it exceeds a critical size set by
its velocity dispersion and density) onto swarm cohesion dynamics --
replacing gravity with a formation-cohesion "attraction" gain -- to detect
the density at which a local drone cluster irreversibly collapses into a
tight kinetic strike formation rather than remaining dispersed.
"""

import numpy as np

DEFAULT_COHESION_GAIN = 1.0


class JeansInstabilityAnalyzer:
    """Evaluates swarm-cluster collapse thresholds via the Jeans criterion."""

    def __init__(self, cohesion_gain=DEFAULT_COHESION_GAIN):
        """Set the cohesion gain, the swarm-formation analog of gravity G."""
        self.cohesion_gain = cohesion_gain

    def calc_jeans_length(self, velocity_dispersion, swarm_density):
        """Evaluate lambda_J = velocity_dispersion * sqrt(pi / (G*rho)).

        Tactical advantage: vectorized over an array of local swarm
        pockets, giving the critical cluster radius above which local
        cohesion overcomes velocity dispersion and the cluster collapses.
        """
        sigma = np.atleast_1d(np.asarray(velocity_dispersion, dtype=float))
        rho = np.atleast_1d(np.asarray(swarm_density, dtype=float))
        return sigma * np.sqrt(np.pi / (self.cohesion_gain * rho))

    def calc_jeans_mass(self, velocity_dispersion, swarm_density):
        """Evaluate the critical drone-count analog of the Jeans mass.

        Tactical advantage: gives a critical member-count threshold for a
        cluster, complementing the spatial Jeans-length criterion.
        """
        sigma = np.atleast_1d(np.asarray(velocity_dispersion, dtype=float))
        rho = np.atleast_1d(np.asarray(swarm_density, dtype=float))
        mass_term = (5.0 * sigma ** 2 / self.cohesion_gain) ** 1.5
        density_term = np.sqrt(3.0 / (4.0 * np.pi * rho))
        return mass_term * density_term

    def evaluate_collapse_risk(
        self, cluster_radius, velocity_dispersion, swarm_density
    ):
        """Flag clusters whose radius exceeds the Jeans length as collapsing.

        Tactical advantage: a single vectorized pass classifies every
        localized swarm pocket as either gravitationally/cohesively stable
        (dispersed) or unstable (collapsing into a strike formation),
        directly actionable for a swarm controller.
        """
        jeans_length = self.calc_jeans_length(
            velocity_dispersion, swarm_density
        )
        radius = np.atleast_1d(np.asarray(cluster_radius, dtype=float))
        will_collapse = radius > jeans_length
        return {
            "jeans_length": jeans_length,
            "will_collapse": will_collapse,
        }
