"""Polyakov string-action surface minimization for adversarial detection.

Flags perturbations such as optical camouflage or adversarial pixel noise.

Tactical use: treats a 2D sensor frame as a worldsheet whose area/curvature
should be smooth under the string action; adversarial patches (optical
camouflage, pixel-level perturbation noise) locally spike the induced-metric
curvature, so a vectorized action-density scan flags the perturbed region
without running a full neural adversarial-detector model.
"""

import numpy as np


class PolyakovRedTeamScanner:
    """Scans 2D sensor frames for high-curvature adversarial-noise regions."""

    def __init__(self, action_threshold=3.0):
        """Set the action-density z-score above which a region is flagged."""
        self.action_threshold = action_threshold

    def _induced_metric_gradients(self, frame):
        """Compute worldsheet embedding gradients (dX/dsigma1, dX/dsigma2)."""
        grad_sigma1 = np.gradient(frame, axis=0)
        grad_sigma2 = np.gradient(frame, axis=1)
        return grad_sigma1, grad_sigma2

    def calc_polyakov_action_density(self, frame):
        """Evaluate the local action density S ~ (dX/ds1)^2 + (dX/ds2)^2.

        Tactical advantage: a single vectorized pass yields a per-pixel
        "surface tension" map; legitimate imagery varies smoothly while
        adversarial perturbations inject high-frequency curvature spikes.
        """
        grad_sigma1, grad_sigma2 = self._induced_metric_gradients(frame)
        return grad_sigma1 ** 2 + grad_sigma2 ** 2

    def detect_adversarial_regions(self, frame):
        """Flag pixels whose action density is a statistical outlier.

        Tactical advantage: replaces a trained adversarial classifier with a
        fast physics-inspired statistical test suitable for edge deployment.
        """
        action_density = self.calc_polyakov_action_density(frame)
        mean_action = np.mean(action_density)
        std_action = np.std(action_density) or 1.0
        z_scores = (action_density - mean_action) / std_action
        flagged_mask = z_scores > self.action_threshold
        return {
            "action_density": action_density,
            "flagged_mask": flagged_mask,
            "flagged_pixel_count": int(np.sum(flagged_mask)),
            "is_adversarial_suspected": bool(np.any(flagged_mask)),
        }
