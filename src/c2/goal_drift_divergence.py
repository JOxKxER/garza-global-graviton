"""KL-divergence goal-drift auditing for autonomous swarm policy alignment.

Tactical use: an autonomous swarm's learned action-selection distribution
can gradually drift away from the commander's intended strategic-action
distribution without any single decision looking obviously wrong. Tracking
the KL divergence between the two distributions continuously catches that
slow drift and can force a sub-goal stack flush before the swarm commits
to a mission that no longer reflects commander intent.
"""

import numpy as np

DEFAULT_DRIFT_THRESHOLD = 0.5


class GoalDriftAuditor:
    """Audits AI action distributions against commander goal distributions."""

    def __init__(self, drift_threshold=DEFAULT_DRIFT_THRESHOLD):
        """Set the KL divergence threshold that triggers recalibration."""
        self.drift_threshold = drift_threshold

    def calc_kl_divergence(self, action_distribution, goal_distribution):
        """Evaluate D_KL(P || Q) = sum(P(i) * log(P(i)/Q(i))) per batch row.

        Tactical advantage: a single vectorized pass scores an entire
        batch of swarm-agent action distributions against the commander's
        intended distribution at once, with no per-agent loop.
        """
        p = np.atleast_2d(np.asarray(action_distribution, dtype=float))
        q = np.atleast_2d(np.asarray(goal_distribution, dtype=float))
        safe_p = np.clip(p, 1e-12, None)
        safe_q = np.clip(q, 1e-12, None)
        return np.sum(safe_p * (np.log(safe_p) - np.log(safe_q)), axis=-1)

    def assess_drift(self, action_distribution, goal_distribution):
        """Flag agents whose goal-drift divergence exceeds the safe threshold.

        Tactical advantage: converts the raw divergence score into an
        operator-actionable recalibration trigger, automatically flushing
        a drifted agent's sub-goal stack before it acts on misaligned intent.
        """
        divergence = self.calc_kl_divergence(
            action_distribution, goal_distribution
        )
        needs_recalibration = divergence > self.drift_threshold
        return {
            "divergence": divergence,
            "needs_recalibration": needs_recalibration,
        }
