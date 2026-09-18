"""Vectorized attestation-verification performance simulator/proxy.

SECURITY NOTE: this module is a NON-CRYPTOGRAPHIC benchmarking proxy that
models the O(1)-per-signature performance profile of Ed25519 command
attestation. It must never be used for real authentication -- it provides
no actual cryptographic security guarantee. Production authentication of
swarm commands must use a vetted, audited implementation (e.g. the
`cryptography` or `PyNaCl` libraries' real Ed25519 verification).

Tactical use: even with real Ed25519 verification, the operational
question is throughput -- can every incoming command in a busy tactical
link be checked against a hard human-authority gate without becoming a
bottleneck. This proxy exercises that same batch-verification data path
end to end for edge-compute capacity planning.
"""

import numpy as np

DEFAULT_HASH_MODULUS = 2 ** 61 - 1
DEFAULT_HASH_BASE = 257


class AttestationSimulator:
    """Simulates batched O(1)-per-signature command attestation checks."""

    def __init__(
        self, hash_base=DEFAULT_HASH_BASE, hash_modulus=DEFAULT_HASH_MODULUS
    ):
        """Set the polynomial-hash base and modulus used by the proxy."""
        self.hash_base = hash_base
        self.hash_modulus = hash_modulus

    def calc_digest_proxy(self, message_bytes, signing_keys):
        """Compute a vectorized polynomial-hash digest proxy for a batch.

        Tactical advantage: not real cryptography, but exercises the same
        "hash every byte of every incoming command, combine with a key,
        compare" data path at the same O(1)-per-signature complexity class
        Ed25519 verification has, for realistic throughput benchmarking.
        """
        messages = np.atleast_2d(np.asarray(message_bytes, dtype=np.int64))
        keys = np.atleast_1d(np.asarray(signing_keys, dtype=np.int64))

        message_length = messages.shape[1]
        base_powers = np.power(
            self.hash_base,
            np.arange(message_length, dtype=np.int64),
            dtype=np.int64,
        )
        weighted = (messages * base_powers[None, :]) % self.hash_modulus
        digest = np.sum(weighted, axis=-1) % self.hash_modulus
        return (digest + keys) % self.hash_modulus

    def verify_batch(self, message_bytes, signing_keys, claimed_signatures):
        """Batch-verify claimed signatures against the recomputed digest proxy.

        Tactical advantage: a single vectorized pass screens an entire
        batch of incoming commands for authenticity, giving a hard
        accept/reject gate before any command reaches an actuator.
        """
        expected = self.calc_digest_proxy(message_bytes, signing_keys)
        claimed = np.atleast_1d(np.asarray(claimed_signatures, dtype=np.int64))
        valid = expected == claimed
        return {
            "valid_mask": valid,
            "accepted_count": int(np.sum(valid)),
            "rejected_count": int(np.sum(~valid)),
        }
