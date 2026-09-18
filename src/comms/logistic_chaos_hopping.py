"""Logistic-map chaotic sequence generator for ECCM frequency hopping.

Tactical use: the logistic map x_{n+1} = r*x_n*(1-x_n) at r=4.0 produces a
deterministic yet statistically unpredictable sequence in O(1) memory per
hopping channel -- both the transmitter and receiver only need to share the
initial seed x0 and rate r, not a stored hop table, to stay synchronized
against an adversary trying to predict or jam the next frequency.
"""

import numpy as np

FULLY_CHAOTIC_RATE = 4.0


class LogisticChaosHopper:
    """Generates deterministic chaotic frequency-hop sequences per node."""

    def __init__(self, chaos_rate=FULLY_CHAOTIC_RATE):
        """Set the logistic map rate r (r=4.0 gives fully chaotic behavior)."""
        if not 0.0 < chaos_rate <= 4.0:
            raise ValueError("chaos_rate must be in (0, 4.0]")
        self.chaos_rate = chaos_rate

    def generate_sequence(self, seed_x0, sequence_length):
        """Iterate the logistic map for one or more parallel seeded chains.

        Tactical advantage: vectorizes across an array of independent node
        seeds so a base station can advance every node's hop sequence in
        lockstep with one call per time step instead of per-node looping.
        """
        seeds = np.atleast_1d(np.asarray(seed_x0, dtype=float))
        if np.any((seeds <= 0.0) | (seeds >= 1.0)):
            raise ValueError("seed_x0 values must lie strictly in (0, 1)")

        sequence = np.empty((sequence_length, seeds.shape[0]))
        current = seeds.copy()
        for step in range(sequence_length):
            sequence[step] = current
            current = self.chaos_rate * current * (1.0 - current)
        return sequence

    def map_to_channels(self, chaotic_sequence, num_channels):
        """Map chaotic values in (0, 1) onto a discrete set of hop channels.

        Tactical advantage: converts the continuous chaotic state directly
        into a jam-resistant channel index sequence with no lookup table.
        """
        scaled = chaotic_sequence * num_channels
        return np.clip(scaled.astype(int), 0, num_channels - 1)
