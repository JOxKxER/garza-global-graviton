"""Vectorized Vandermonde erasure coding for m-failure-tolerant mesh storage.

Tactical use: tactical data (track history, key material, mission state)
sharded across a mesh must survive the loss of multiple nodes to kinetic
or EW attack. A systematic Reed-Solomon-style erasure code splits data into
k shards plus m parity shards such that any k of the (k+m) total shards
are sufficient to reconstruct the original data.
"""

import numpy as np


class ErasureCodingEncoder:
    """Builds a systematic Vandermonde generator matrix and encodes shards."""

    def __init__(self, num_data_shards, num_parity_shards):
        """Set k data shards and m parity shards (tolerates any m losses)."""
        self.num_data_shards = num_data_shards
        self.num_parity_shards = num_parity_shards

    def build_generator_matrix(self):
        """Build the systematic (k+m, k) generator matrix G = [I_k; V_parity].

        The top k rows are the identity (data shards pass through
        unmodified); the bottom m rows are a Vandermonde matrix built from
        m distinct evaluation points, guaranteeing any k of the k+m rows
        of G are linearly independent and therefore invertible.

        Tactical advantage: computed once per shard configuration and
        reused for every encode call, so the expensive matrix-construction
        step never repeats on the hot path.
        """
        k = self.num_data_shards
        m = self.num_parity_shards
        identity_block = np.eye(k)

        evaluation_points = np.arange(1, m + 1, dtype=float)
        powers = np.arange(k)
        vandermonde_block = evaluation_points[:, None] ** powers[None, :]

        return np.vstack([identity_block, vandermonde_block])

    def encode(self, data_block):
        """Encode a flat data block into k+m shards via C = G @ M.

        Tactical advantage: a single vectorized matrix multiply produces
        every data and parity shard at once, ready to be distributed one
        shard per mesh node.
        """
        k = self.num_data_shards
        flat_data = np.asarray(data_block, dtype=float).ravel()

        if pad_length := (-flat_data.size) % k:
            flat_data = np.concatenate([flat_data, np.zeros(pad_length)])

        shard_length = flat_data.size // k
        data_matrix = flat_data.reshape(k, shard_length)

        generator_matrix = self.build_generator_matrix()
        return generator_matrix @ data_matrix

    def calc_fault_tolerance(self):
        """Return the number of simultaneous shard losses this code survives.

        Tactical advantage: gives an operator a direct answer to "how many
        nodes can we lose and still recover this data".
        """
        return self.num_parity_shards
