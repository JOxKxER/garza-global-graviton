"""Covariance Intersection fusion for consistent multi-agent track fusion.

Tactical use: naively averaging two sensor tracks' covariances (e.g. radar
and optronics) assumes independent errors and produces an overconfident
fused estimate when the true cross-correlation is unknown -- a serious risk
in GPS-denied environments where errors are often correlated. Covariance
Intersection guarantees a consistent (non-overconfident) fused covariance
for any unknown correlation.
"""

import numpy as np

DEFAULT_OMEGA_SEARCH_STEPS = 101


class CovarianceIntersectionFuser:
    """Fuses two covariance estimates via consistency-preserving CI fusion."""

    def __init__(self, omega_search_steps=DEFAULT_OMEGA_SEARCH_STEPS):
        """Set the resolution of the vectorized omega search grid."""
        self.omega_search_steps = omega_search_steps

    def fuse_covariances(self, covariance_1, covariance_2, criterion="trace"):
        """Fuse P1, P2 via P^-1 = w*P1^-1 + (1-w)*P2^-1 at the optimal w.

        Searches a vectorized grid of candidate omega in [0, 1], batch
        inverting all candidate fused-information matrices at once, and
        selects the omega minimizing the trace or determinant of the fused
        covariance (a proxy for minimizing fused uncertainty volume).

        Tactical advantage: produces a single fused track covariance that
        is always at least as conservative as either sensor alone, so a
        fire-control solution built on it cannot be overconfident even when
        the two sensors' errors are secretly correlated.
        """
        info_1 = np.linalg.inv(covariance_1)
        info_2 = np.linalg.inv(covariance_2)

        omega_grid = np.linspace(0.0, 1.0, self.omega_search_steps)
        fused_information = (
            omega_grid[:, None, None] * info_1[None, :, :]
            + (1.0 - omega_grid[:, None, None]) * info_2[None, :, :]
        )
        fused_covariance_candidates = np.linalg.inv(fused_information)

        if criterion == "determinant":
            scores = np.linalg.det(fused_covariance_candidates)
        else:
            scores = np.trace(fused_covariance_candidates, axis1=1, axis2=2)

        best_index = np.argmin(scores)
        return {
            "optimal_omega": float(omega_grid[best_index]),
            "fused_covariance": fused_covariance_candidates[best_index],
            "score": float(scores[best_index]),
        }
