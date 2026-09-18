"""Chi-squared (Mahalanobis) gating for track-to-measurement validation.

Tactical use: dense clutter and DRFM (digital radio frequency memory) false
targets can flood a tracker with plausible-looking returns; gating rejects
any measurement whose statistical distance from the predicted track state
is inconsistent with the filter's own uncertainty, before it ever reaches
the Kalman update step.
"""

import numpy as np


class ChiSquaredGate:
    """Computes Mahalanobis distances and applies a chi-squared gate."""

    def __init__(self, gate_threshold=9.21):
        """Set the chi-squared gate (default: 99% confidence, 2 DOF)."""
        self.gate_threshold = gate_threshold

    def calc_mahalanobis_distance_sq(
        self, measurements, predicted_measurement, innovation_covariance
    ):
        """Evaluate d^2 = (z - zhat)^T S^-1 (z - zhat) for a batch of returns.

        Tactical advantage: one matrix inverse plus one vectorized einsum
        scores an entire batch of radar returns against the track's
        predicted state and uncertainty, with no per-return loop.
        """
        innovation = measurements - predicted_measurement
        inverse_covariance = np.linalg.inv(innovation_covariance)
        return np.einsum(
            "ni,ij,nj->n", innovation, inverse_covariance, innovation
        )

    def gate_measurements(
        self, measurements, predicted_measurement, innovation_covariance
    ):
        """Accept only measurements whose Mahalanobis distance clears the gate.

        Tactical advantage: strictly rejects clutter and spoofed returns
        before they can corrupt the core Kalman filter state, while passing
        through legitimate returns even under heavy false-target density.
        """
        distances_sq = self.calc_mahalanobis_distance_sq(
            measurements, predicted_measurement, innovation_covariance
        )
        accepted_mask = distances_sq < self.gate_threshold
        return {
            "distances_sq": distances_sq,
            "accepted_mask": accepted_mask,
            "accepted_count": int(np.sum(accepted_mask)),
            "rejected_count": int(np.sum(~accepted_mask)),
        }
