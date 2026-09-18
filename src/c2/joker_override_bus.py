"""Joker Override Translation Bus: semantic intent to precision weight updates.

Tactical use: Joker's cognitive layer reasons in a semantic strategic-
category space, but the Master Active Inference Node's fast physical loop
only understands numeric per-sensor precision weights. This bus translates
Joker's asynchronous strategic-shift output into a concrete precision
weight update the physical loop can ingest on its very next tick, closing
the loop between slow semantic reasoning and fast physical control.
"""

import numpy as np

DEFAULT_OVERRIDE_GAIN = 1.0


class JokerOverrideBus:
    """Translates Joker's semantic output into sensor weight updates."""

    def __init__(self, override_gain=DEFAULT_OVERRIDE_GAIN):
        """Set the gain scaling how strongly Joker's intent reweights sensors.

        Kept as a single tunable so operators can dial down AI authority.
        """
        self.override_gain = override_gain

    def translate_to_precision_weights(
        self, semantic_output, sensor_class_assignments
    ):
        """Map a per-category semantic output onto per-sensor weight updates.

        Each sensor stream is assigned to one of Joker's strategic
        categories; every sensor in that category receives the same
        category-level weight from Joker's semantic output.

        Tactical advantage: a single vectorized gather translates Joker's
        compact strategic decision into a full per-sensor weight update
        for an entire swarm's sensor bank at once, with no per-sensor loop.
        """
        semantic = np.atleast_1d(np.asarray(semantic_output, dtype=float))
        assignments = np.atleast_1d(
            np.asarray(sensor_class_assignments, dtype=np.int64)
        )
        return self.override_gain * semantic[assignments]

    def apply_override(
        self,
        existing_precision_weights,
        semantic_output,
        sensor_class_assignments,
    ):
        """Blend Joker's translated override into the current weights.

        Tactical advantage: produces the exact `ai_precision_weights` array
        the Master Active Inference Node's precision scaler can consume on
        its next tick, folding Joker's strategic intent directly into the
        fast physical control loop.
        """
        override_weights = self.translate_to_precision_weights(
            semantic_output, sensor_class_assignments
        )
        current = np.atleast_1d(
            np.asarray(existing_precision_weights, dtype=float)
        )
        return current * override_weights
