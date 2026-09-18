"""Mori-Zwanzig memory-kernel extraction via recursive Volterra deconvolution.

Tactical use: a Markovian state-tracking model assumes the future depends
only on the present, ignoring any lingering influence of past execution
history. The Mori-Zwanzig formalism instead models a system's
autocorrelation via a memory kernel K(t) in the generalized Langevin
equation dC(t)/dt = -integral(K(t-s) C(s) ds, 0, t); this module extracts
K numerically from an observed C(t) and its derivative via the standard
trapezoidal-rule recursive (Volterra) deconvolution used in statistical
mechanics to recover non-Markovian memory effects from time-series data.
"""

from __future__ import annotations

import numpy as np


def _trapezoidal_weights(num_points: int) -> np.ndarray:
    """Return composite trapezoidal quadrature weights for num_points."""
    if num_points == 1:
        return np.array([1.0])
    weights = np.ones(num_points)
    weights[0] = 0.5
    weights[-1] = 0.5
    return weights


class MoriZwanzigKernelEstimator:
    """Extracts and re-applies non-Markovian kernels via Volterra sums."""

    def __init__(self, time_step: float) -> None:
        """Set the uniform time step Delta_t of the sampled time series."""
        if time_step <= 0.0:
            raise ValueError("time_step must be positive")
        self.time_step = time_step

    def convolve_kernel(self, kernel, autocorrelation) -> np.ndarray:
        """Forward-apply K to C via the discretized Volterra memory integral.

        Evaluates dC/dt|_n = -Delta_t * sum_{m=0}^{n} w_m * K_m * C_{n-m}
        using composite trapezoidal weights w, for every sample index n.

        Tactical advantage: a single explicit forward model whose exact
        algebraic inverse (see `estimate_kernel`) guarantees round-trip
        consistency by construction, rather than by coincidence.
        """
        k = np.asarray(kernel, dtype=float)
        c = np.asarray(autocorrelation, dtype=float)
        num_points = c.shape[0]
        derivative = np.zeros(num_points)

        for n in range(num_points):
            weights = _trapezoidal_weights(n + 1)
            history = c[n::-1]  # C[n], C[n-1], ..., C[0]
            derivative[n] = -self.time_step * np.sum(
                weights * k[: n + 1] * history
            )
        return derivative

    def estimate_kernel(self, autocorrelation, derivative) -> np.ndarray:
        """Recursively deconvolve K from an observed C(t) and its derivative.

        Solves the same triangular Volterra system as `convolve_kernel`
        via forward substitution: at each step n, every K_0..K_{n-1} is
        already known, leaving one linear equation in the single unknown
        K_n.

        Tactical advantage: an exact recursive solve (not an
        approximation), so re-applying `convolve_kernel` to the result
        reproduces the input derivative to numerical precision.
        """
        c = np.asarray(autocorrelation, dtype=float)
        d = np.asarray(derivative, dtype=float)
        if c[0] == 0.0:
            raise ValueError("autocorrelation[0] must be nonzero")

        num_points = c.shape[0]
        kernel = np.zeros(num_points)

        for n in range(num_points):
            weights = _trapezoidal_weights(n + 1)
            if n == 0:
                kernel[0] = -d[0] / (self.time_step * weights[0] * c[0])
                continue

            history = c[n:0:-1]  # C[n], C[n-1], ..., C[1]
            partial_sum = np.sum(weights[:n] * kernel[:n] * history)
            kernel[n] = (
                -d[n] / self.time_step - partial_sum
            ) / (weights[n] * c[0])

        return kernel


if __name__ == "__main__":
    demo_time_step = 0.05
    num_samples = 60
    time_axis = np.arange(num_samples) * demo_time_step

    # Synthetic normalized autocorrelation and a known "true" kernel.
    demo_autocorrelation = np.exp(-time_axis / 1.5)
    true_kernel = 4.0 * np.exp(-time_axis / 0.4)

    estimator = MoriZwanzigKernelEstimator(time_step=demo_time_step)
    target_derivative = estimator.convolve_kernel(
        true_kernel, demo_autocorrelation
    )

    estimated_kernel = estimator.estimate_kernel(
        demo_autocorrelation, target_derivative
    )
    reconstructed_derivative = estimator.convolve_kernel(
        estimated_kernel, demo_autocorrelation
    )

    assert np.allclose(
        reconstructed_derivative, target_derivative, atol=1e-8
    ), "Round-trip kernel deconvolution failed to reproduce the derivative."

    print("MoriZwanzigKernelEstimator self-test passed.")
    print(f"Samples: {num_samples}, time_step: {demo_time_step}")
    max_error = np.max(np.abs(reconstructed_derivative - target_derivative))
    print(f"Max round-trip reconstruction error: {max_error:.3e}")
