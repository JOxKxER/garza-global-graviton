"""Cauchy residue extraction for pole-based de-jamming of dense EW noise.

Tactical use: a true target return behaves like a pole of a complex
transfer function -- a sharp, localized singularity -- while dense plasma
sheath or EW noise contributes a smooth, non-singular background. The
Cauchy residue theorem lets a receiver numerically isolate the strength of
any suspected pole location via a small contour integral, separating real
target signal from background jamming without needing to solve for the
transfer function analytically.
"""

import numpy as np

DEFAULT_CONTOUR_RADIUS = 0.05
DEFAULT_CONTOUR_POINTS = 64


class CauchyResidueExtractor:
    """Extracts residues at candidate signal poles via contour integration."""

    def __init__(
        self,
        contour_radius=DEFAULT_CONTOUR_RADIUS,
        num_contour_points=DEFAULT_CONTOUR_POINTS,
    ):
        """Set the small contour radius r and angular sample count M."""
        self.contour_radius = contour_radius
        self.num_contour_points = num_contour_points

    def build_contour_points(self, pole_estimates):
        """Build the (N, M) grid of complex sample points circling each pole.

        Tactical advantage: vectorized construction of every candidate
        pole's evaluation contour at once, ready for a single batched
        signal-function evaluation.
        """
        poles = np.atleast_1d(np.asarray(pole_estimates, dtype=complex))
        theta = np.linspace(
            0.0, 2.0 * np.pi, self.num_contour_points, endpoint=False
        )
        offsets = self.contour_radius * np.exp(1j * theta)
        return poles[:, None] + offsets[None, :], theta

    def extract_residues(self, signal_function, pole_estimates):
        """Evaluate Res(f, z0) ~= (r/M) * sum(f(z_j) * e^(i*theta_j)).

        Discretizes the Cauchy integral formula over a small circular
        contour around each candidate pole, using a signal_function that
        must accept and return complex numpy arrays elementwise.

        Tactical advantage: a single vectorized pass scores every
        candidate pole location for true-target likelihood at once; true
        target poles produce a large-magnitude residue while noise-only
        locations produce a residue near zero.
        """
        contour_points, theta = self.build_contour_points(pole_estimates)
        function_values = signal_function(contour_points)
        weighting = np.exp(1j * theta)[None, :]
        return (self.contour_radius / self.num_contour_points) * np.sum(
            function_values * weighting, axis=-1
        )

    def identify_true_targets(
        self, signal_function, pole_estimates, magnitude_threshold=0.1
    ):
        """Flag candidate poles whose residue magnitude clears a threshold.

        Tactical advantage: converts raw residue values into a direct
        target/no-target classification, rejecting locations dominated by
        smooth EW noise rather than a genuine signal singularity.
        """
        residues = self.extract_residues(signal_function, pole_estimates)
        magnitude = np.abs(residues)
        return {
            "residues": residues,
            "is_true_target": magnitude > magnitude_threshold,
        }
