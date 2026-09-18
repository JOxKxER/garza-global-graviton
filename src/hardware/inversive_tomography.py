"""Inversive tomography for boundary-to-bulk subsurface anomaly mapping.

Tactical use: a 2D array of surface impedance sensors cannot directly see
a buried void or a silent stealth asset moving underground, but their
collective boundary field is causally linked to the 3D bulk structure
beneath it. A regularized (Tikhonov) matrix-inversion proxy recovers the
most likely bulk anomaly profile consistent with the observed boundary
field, without needing an expensive full 3D forward-model solve.
"""

import numpy as np

DEFAULT_REGULARIZATION = 0.1


class InversiveTomographyMapper:
    """Inverts a boundary impedance field into a bulk anomaly proxy."""

    def __init__(self, regularization_lambda=DEFAULT_REGULARIZATION):
        """Set the Tikhonov regularization strength lambda."""
        self.regularization_lambda = regularization_lambda

    def calc_inversion_operator(self, boundary_impedance_matrix):
        """Precompute (Z^T Z + lambda^2 I)^-1 Z^T for a fixed sensor geometry.

        Tactical advantage: computed once per sensor array layout and
        reused across every subsequent boundary reading, so the expensive
        matrix inversion never repeats on the hot scanning path.
        """
        z = np.asarray(boundary_impedance_matrix, dtype=float)
        identity = np.eye(z.shape[1])
        gramian = z.T @ z + (self.regularization_lambda ** 2) * identity
        return np.linalg.solve(gramian, z.T)

    def calc_bulk_anomaly(
        self, boundary_impedance_matrix, observed_boundary_field
    ):
        """Map a batch of observed boundary fields to bulk anomaly profiles.

        Tactical advantage: a single vectorized matrix multiply converts
        an entire batch of live surface-sensor scans into depth-resolved
        bulk anomaly estimates at once, suitable for continuous
        subsurface void or silent-asset tracking.
        """
        inversion_operator = self.calc_inversion_operator(
            boundary_impedance_matrix
        )
        observations = np.atleast_2d(
            np.asarray(observed_boundary_field, dtype=float)
        )
        return observations @ inversion_operator.T

    def detect_anomaly_regions(
        self, boundary_impedance_matrix, observed_boundary_field, threshold=1.0
    ):
        """Flag bulk locations whose anomaly magnitude clears a floor.

        Tactical advantage: converts the raw inverted bulk field into a
        direct target/void detection map for an operator.
        """
        bulk_anomaly = self.calc_bulk_anomaly(
            boundary_impedance_matrix, observed_boundary_field
        )
        return {
            "bulk_anomaly": bulk_anomaly,
            "anomaly_detected": np.abs(bulk_anomaly) > threshold,
        }
