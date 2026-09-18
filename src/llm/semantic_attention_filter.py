"""Scaled dot-product attention for firehose telemetry compression.

Tactical use: Joker cannot digest the raw physical telemetry firehose
without context-bloat overwhelming its limited edge-LLM context window.
Scaled dot-product attention compresses an arbitrarily large batch of
telemetry values down to a single high-value context vector per query,
letting Joker reason over a compact semantic summary instead of raw
sensor floods.
"""

import numpy as np

from src.utils.math_utils import softmax


class SemanticAttentionFilter:
    """Computes scaled dot-product attention over telemetry key/value pairs."""

    def calc_attention(self, query, keys, values):
        """Evaluate Softmax(Q K^T / sqrt(d_k)) V for a batch of telemetry.

        Tactical advantage: a single vectorized pass scores an entire
        batch of telemetry keys against Joker's current query at once,
        weighting each reading by relevance before summarizing it into
        one compact context vector.
        """
        q = np.atleast_2d(np.asarray(query, dtype=float))
        k = np.atleast_2d(np.asarray(keys, dtype=float))
        v = np.atleast_2d(np.asarray(values, dtype=float))

        key_dimension = k.shape[-1]
        scores = (q @ k.T) / np.sqrt(key_dimension)
        attention_weights = softmax(scores)
        return attention_weights @ v

    def compress_telemetry_stream(self, query, telemetry_values, keys=None):
        """Compress a telemetry value stream into one context vector for Joker.

        Tactical advantage: gives Joker a fixed-size, information-dense
        summary of an arbitrarily large telemetry batch, regardless of
        how many raw sensor readings were collected this tick.
        """
        values = np.atleast_2d(np.asarray(telemetry_values, dtype=float))
        effective_keys = values if keys is None else keys
        return self.calc_attention(query, effective_keys, values)
