"""Particle filter weight update and resampling for non-Gaussian tracking.

Tactical use: a hypersonic target that unpredictably splits (decoys) or
deploys countermeasures breaks the unimodal-Gaussian assumption behind a
Kalman filter. A particle filter instead represents the target's belief
state as a weighted point cloud, so multimodal hypotheses (real body vs.
decoys) survive until sensor evidence collapses them.
"""

import numpy as np


class ParticleResampler:
    """Updates particle weights from measurement likelihoods and resamples."""

    def update_weights(self, prior_weights, measurement_likelihoods):
        """Compute w_t^i proportional to w_{t-1}^i * P(z_t | x_t^i).

        Tactical advantage: a single vectorized multiply-and-normalize pass
        folds new sensor evidence into every particle's belief weight at
        once, regardless of how many split/decoy hypotheses are tracked.
        """
        unnormalized = prior_weights * measurement_likelihoods
        total_weight = np.sum(unnormalized)
        if total_weight <= 0:
            return np.full_like(prior_weights, 1.0 / prior_weights.size)
        return unnormalized / total_weight

    def effective_sample_size(self, weights):
        """Compute N_eff = 1 / sum(w_i^2), the degeneracy diagnostic.

        Tactical advantage: a cheap scalar test for when the particle set
        has collapsed onto too few hypotheses and needs resampling.
        """
        return 1.0 / np.sum(weights ** 2)

    def systematic_resample(self, particles, weights, random_state=None):
        """Draw a new equally-weighted particle set via systematic resampling.

        Tactical advantage: an O(N) vectorized resampling step (via cumsum
        and searchsorted, no per-particle loop) that concentrates the point
        cloud onto surviving hypotheses -- e.g. the real body after decoys
        are ruled out by measurement likelihood -- in real time.
        """
        rng = np.random.default_rng() if random_state is None else random_state
        num_particles = particles.shape[0]
        cumulative_weights = np.cumsum(weights)
        cumulative_weights[-1] = 1.0

        start = rng.uniform(0, 1.0 / num_particles)
        pointers = start + np.arange(num_particles) / num_particles
        indices = np.searchsorted(cumulative_weights, pointers)

        resampled_particles = particles[indices]
        resampled_weights = np.full(num_particles, 1.0 / num_particles)
        return resampled_particles, resampled_weights
