"""Vectorized 1D Wasserstein optimal transport for swarm formation morphing.

Tactical use: reshaping a swarm from one geographic formation to another is
an optimal-transport problem -- minimize total displacement work while
moving mass (drones) from the old distribution to the new one. For 1D
empirical distributions the exact Wasserstein distance and transport
correspondence reduce to a simple sort, avoiding a full linear program.
"""

import numpy as np


class WassersteinTransportPlanner:
    """Computes 1D Wasserstein distances and morph interpolations."""

    def calc_distance_1d(self, samples_a, samples_b, order=2):
        """Evaluate W_p(A, B) for batches of 1D empirical distributions.

        Sorting each distribution's samples gives the exact optimal
        1D transport correspondence (i-th smallest maps to i-th smallest),
        so the distance reduces to a sorted elementwise norm.

        Tactical advantage: a single vectorized sort-and-norm pass scores
        an entire batch of candidate old-formation/new-formation pairs at
        once, letting a planner pick the lowest-energy morph.
        """
        a_sorted = np.sort(np.atleast_2d(samples_a), axis=-1)
        b_sorted = np.sort(np.atleast_2d(samples_b), axis=-1)
        absolute_diff = np.abs(a_sorted - b_sorted) ** order
        return np.mean(absolute_diff, axis=-1) ** (1.0 / order)

    def calc_transport_correspondence(self, samples_a, samples_b):
        """Return the sorted-index correspondence realizing the optimal plan.

        Tactical advantage: gives each drone in formation A its exact
        assigned destination in formation B under the minimal-energy
        transport plan, ready to hand to a per-drone path planner.
        """
        order_a = np.argsort(np.atleast_2d(samples_a), axis=-1)
        order_b = np.argsort(np.atleast_2d(samples_b), axis=-1)
        return order_a, order_b

    def interpolate_morph(self, samples_a, samples_b, morph_fraction):
        """Compute the displacement-interpolated formation at time t in [0, 1].

        Tactical advantage: a single vectorized blend of the two sorted
        distributions yields a smooth, minimal-energy intermediate
        formation for any fraction of the morph, not just the endpoints.
        """
        a_sorted = np.sort(np.atleast_2d(samples_a), axis=-1)
        b_sorted = np.sort(np.atleast_2d(samples_b), axis=-1)
        return (1.0 - morph_fraction) * a_sorted + morph_fraction * b_sorted
