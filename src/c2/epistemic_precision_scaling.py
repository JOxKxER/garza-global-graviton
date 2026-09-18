"""Epistemic precision scaling for authenticated human C2 authority.

Tactical use: once a human command is cryptographically verified, any
conflicting AI-driven sensor policy must be immediately and mathematically
subordinated -- not merely outvoted in a tie-break, but structurally
suppressed in the fused confidence weighting -- so the fused decision
surface cannot drift back toward the AI's prior recommendation.
"""

import numpy as np

DEFAULT_SUPPRESSION_FACTOR = 0.01


class EpistemicPrecisionScaler:
    """Suppresses AI sensor-policy precision weights under human override."""

    def __init__(self, suppression_factor=DEFAULT_SUPPRESSION_FACTOR):
        """Set the multiplicative suppression factor applied to AI weights."""
        self.suppression_factor = suppression_factor

    def calc_scaled_precision(
        self, ai_precision_weights, human_override_flags
    ):
        """Suppress AI precision weights wherever a human override is active.

        Tactical advantage: a single vectorized pass re-weights an entire
        bank of parallel sensor/policy streams at once, guaranteeing
        verified human intent structurally dominates the fused estimate
        rather than merely breaking ties with it.
        """
        weights = np.atleast_1d(
            np.asarray(ai_precision_weights, dtype=float)
        )
        override = np.atleast_1d(
            np.asarray(human_override_flags, dtype=bool)
        )
        suppression = np.where(override, self.suppression_factor, 1.0)
        return weights * suppression

    def calc_authority_ratio(self, ai_precision_weights, human_override_flags):
        """Evaluate how much of the original AI weight remains after scaling.

        Tactical advantage: a direct, auditable figure showing exactly how
        subordinated the AI policy has become under human authority, for
        after-action review of contested engagements.
        """
        scaled = self.calc_scaled_precision(
            ai_precision_weights, human_override_flags
        )
        original = np.atleast_1d(
            np.asarray(ai_precision_weights, dtype=float)
        )
        safe_original = np.where(original == 0, 1.0, original)
        return scaled / safe_original
