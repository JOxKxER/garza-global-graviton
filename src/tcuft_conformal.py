"""Conformal (Weyl) rescaling of the flat Minkowski metric for multi-scale ops.

Tactical use: lets the C2 engine rescale a single flat-spacetime metric
between orbital-scale and micro-swarm-scale operations without swapping to a
different model, and lets it verify a field configuration is curvature-free
before trusting it for beam steering or lossless transport.
"""

import numpy as np


class TCUFTEngine:
    """Scales a flat Minkowski metric conformally and checks flatness."""

    def __init__(self):
        """Initialize the flat Minkowski metric diag(-1, 1, 1, 1)."""
        self.eta = np.diag([-1, 1, 1, 1])

    def conformal_transformation(self, omega_scale_factor):
        """Apply local conformal symmetry scaling: g_uv = Omega^2 * eta_uv.

        Tactical advantage: allows the engine to scale from orbital (macro)
        to micro-swarm operations seamlessly using one metric object.
        """
        return (omega_scale_factor ** 2) * self.eta

    def check_flatness(self, field_strength_tensor):
        """Evaluate F = dA + A^A = 0 (zero-curvature flatness).

        Tactical advantage: used for beam steering and dissipationless
        transport validation before a field configuration is trusted.
        """
        return np.allclose(
            field_strength_tensor, np.zeros_like(field_strength_tensor)
        )
