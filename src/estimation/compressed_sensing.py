"""ISTA compressed-sensing recovery for sub-Nyquist sparse sensor sampling.

Tactical use: heavy EW jamming often forces a sensor to collect far fewer
samples than Nyquist would require. If the true scene is sparse in some
basis (a common property of radar/optical returns), compressed sensing can
still reconstruct a high-fidelity frame from those few measurements via
L1-regularized recovery, with ISTA as its simplest iterative solver.
"""

import numpy as np


class CompressedSensingReconstructor:
    """Reconstructs sparse signals from compressed measurements via ISTA."""

    def __init__(self, step_size=0.5, sparsity_threshold=0.05):
        """Set the ISTA step size alpha and the soft-threshold lambda."""
        self.step_size = step_size
        self.sparsity_threshold = sparsity_threshold

    def soft_threshold(self, values, threshold):
        """Evaluate soft_thresh(v, lambda) = sign(v) * max(|v| - lambda, 0).

        Tactical advantage: the core sparsity-enforcing shrinkage step,
        vectorized elementwise across an entire candidate signal at once.
        """
        return np.sign(values) * np.maximum(
            np.abs(values) - threshold, 0.0
        )

    def ista_step(self, x_estimate, sensing_matrix, measurements):
        """Evaluate one ISTA update x_{k+1} = soft_thresh(x_k + a*A^T(y-Ax_k)).

        Tactical advantage: a single vectorized matrix-vector residual and
        shrinkage step, batched across every parallel signal being
        reconstructed at once.
        """
        residual = measurements - sensing_matrix @ x_estimate
        gradient_step = x_estimate + self.step_size * (
            sensing_matrix.T @ residual
        )
        return self.soft_threshold(gradient_step, self.sparsity_threshold)

    def reconstruct(
        self, measurements, sensing_matrix, num_iterations=100, x0=None
    ):
        """Run ISTA for a fixed iteration count to recover a sparse signal.

        Tactical advantage: recovers a full-resolution radar/optical frame
        from a sparse sub-Nyquist measurement vector, letting a jammed
        sensor still deliver an actionable picture instead of a gap.
        """
        num_features = sensing_matrix.shape[1]
        x_estimate = (
            np.zeros(num_features) if x0 is None else np.asarray(x0)
        )
        for _ in range(num_iterations):
            x_estimate = self.ista_step(
                x_estimate, sensing_matrix, measurements
            )
        return x_estimate
