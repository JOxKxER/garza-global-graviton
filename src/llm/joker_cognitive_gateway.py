"""Joker LLM cognitive gateway: quantized edge-LLM KV-cache update proxy.

PRODUCTION NOTE: this module is a throughput-benchmarking proxy, not a
real language model. In production this node interfaces with a local
4-bit quantized edge LLM runtime (e.g. llama.cpp or an ONNX Runtime
quantized transformer) running as an asynchronous cognitive supervisor
above the Master Active Inference Node's fast physical control loop.

Tactical use: the Master Active Inference Node runs its physical control
cycle at tens of kilohertz and cannot wait on LLM inference. Joker instead
runs on its own cadence, incrementally updating a sliding-window KV cache
one token at a time -- the dominant per-step cost in real quantized
transformer inference -- so this proxy exercises the same data path and
matrix-multiply cost profile a real edge LLM integration would see.
"""

import numpy as np

DEFAULT_HIDDEN_DIM = 4096
DEFAULT_CONTEXT_LENGTH = 1024
DEFAULT_QUANTIZATION_BITS = 4


class JokerCognitiveGateway:
    """Simulates a sliding-window KV-cache update step for an edge LLM."""

    def __init__(
        self,
        hidden_dim=DEFAULT_HIDDEN_DIM,
        context_length=DEFAULT_CONTEXT_LENGTH,
        quantization_bits=DEFAULT_QUANTIZATION_BITS,
    ):
        """Set the hidden dimension, context window, and quant bit-width."""
        self.hidden_dim = hidden_dim
        self.context_length = context_length
        self.quantization_bits = quantization_bits
        self.key_projection = np.random.normal(
            0, 1.0 / np.sqrt(hidden_dim), (hidden_dim, hidden_dim)
        )
        self.value_projection = np.random.normal(
            0, 1.0 / np.sqrt(hidden_dim), (hidden_dim, hidden_dim)
        )

    def build_kv_cache(self):
        """Allocate an initial (context_length, hidden_dim) key/value cache.

        Tactical advantage: a fixed-size sliding-window cache bounds
        Joker's per-tick memory and compute footprint regardless of how
        long the mission has been running.
        """
        cache_shape = (self.context_length, self.hidden_dim)
        return np.zeros(cache_shape), np.zeros(cache_shape)

    def update_step(self, incoming_token_embedding, cache_keys, cache_values):
        """Project a new token and roll it into the sliding-window KV cache.

        Tactical advantage: the projection matmul is the dominant cost of
        real quantized-transformer decoding; benchmarking it in isolation
        gives an accurate per-token latency figure for edge-LLM capacity
        planning before the real model is integrated.
        """
        embedding = np.asarray(incoming_token_embedding, dtype=float)
        new_key = embedding @ self.key_projection
        new_value = embedding @ self.value_projection

        updated_keys = np.roll(cache_keys, -1, axis=0)
        updated_values = np.roll(cache_values, -1, axis=0)
        updated_keys[-1] = new_key
        updated_values[-1] = new_value
        return updated_keys, updated_values
