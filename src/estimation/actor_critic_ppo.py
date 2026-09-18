"""PPO clipped surrogate objective for stable swarm policy optimization.

Tactical use: naive policy-gradient updates can overshoot and catastrophically
collapse a swarm's learned evasive-maneuver policy after a single bad
batch of experience. Clipping the policy-ratio term bounds how far a single
update can move the policy, letting a swarm learn from live engagement
data continuously without risking a sudden loss of trained behavior.
"""

import numpy as np

DEFAULT_CLIP_EPSILON = 0.2


class PpoClippedObjective:
    """Evaluates the PPO clipped surrogate objective for policy updates."""

    def __init__(self, clip_epsilon=DEFAULT_CLIP_EPSILON):
        """Set the clip range epsilon bounding the policy trust region."""
        self.clip_epsilon = clip_epsilon

    def calc_clipped_objective(self, probability_ratios, advantages):
        """Evaluate L^CLIP = mean(min(r*A, clip(r, 1-e, 1+e)*A)).

        Tactical advantage: a single vectorized pass scores an entire
        batch of sampled (state, action) experiences at once, giving a
        stable per-update training signal safe to apply continuously
        during live operations.
        """
        r = np.atleast_1d(np.asarray(probability_ratios, dtype=float))
        a_hat = np.atleast_1d(np.asarray(advantages, dtype=float))

        unclipped_term = r * a_hat
        clipped_ratio = np.clip(
            r, 1.0 - self.clip_epsilon, 1.0 + self.clip_epsilon
        )
        clipped_term = clipped_ratio * a_hat

        per_sample_objective = np.minimum(unclipped_term, clipped_term)
        return {
            "per_sample_objective": per_sample_objective,
            "mean_objective": float(np.mean(per_sample_objective)),
        }

    def calc_trust_region_violation_rate(self, probability_ratios):
        """Fraction of samples whose ratio fell outside the trust region.

        Tactical advantage: a cheap diagnostic for how aggressively the
        policy is drifting, useful for tuning the learning rate or clip
        range before instability sets in.
        """
        r = np.atleast_1d(np.asarray(probability_ratios, dtype=float))
        outside = (r < 1.0 - self.clip_epsilon) | (
            r > 1.0 + self.clip_epsilon
        )
        return float(np.mean(outside))
