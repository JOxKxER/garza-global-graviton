"""Birthday-bound collision probability for hash and key-rotation auditing.

Tactical use: instantly audits whether a session-key or hash identifier
space is large enough for a swarm's expected traffic volume, and derives
how many sessions can safely elapse before key rotation is mandatory --
critical under EW conditions where an adversary is actively harvesting
traffic to force a collision.
"""

import numpy as np


class BirthdayBoundAuditor:
    """Evaluates birthday-bound collision risk for hash/key space sizing."""

    def calc_collision_probability(self, sample_count, hash_bits):
        """Evaluate P ~= 1 - exp(-n^2 / (2*m)), m = 2^hash_bits.

        Tactical advantage: vectorized over arrays of candidate session
        counts and/or hash-bit widths, auditing an entire fleet of
        proposed channel configurations in one call.
        """
        n = np.atleast_1d(np.asarray(sample_count, dtype=float))
        bits = np.atleast_1d(np.asarray(hash_bits, dtype=float))
        hash_space_size = np.exp2(bits)
        exponent = -(n ** 2) / (2.0 * hash_space_size)
        return 1.0 - np.exp(exponent)

    def calc_required_bits(self, sample_count, target_probability):
        """Solve for the minimum hash bit-length holding P below a target.

        Tactical advantage: gives a concrete "use at least N bits" floor
        for a hash/key scheme before it is deployed, rather than
        discovering an inadequate bit-length after a collision occurs.
        """
        n = np.atleast_1d(np.asarray(sample_count, dtype=float))
        p_target = target_probability
        hash_space_size = -(n ** 2) / (2.0 * np.log(1.0 - p_target))
        return np.log2(hash_space_size)

    def calc_safe_session_count(self, hash_bits, target_probability):
        """Solve for the max sessions before rotation is required.

        Tactical advantage: gives a swarm's key-management schedule a
        concrete rotate-after-N-sessions trigger derived directly from the
        deployed hash width and the accepted collision-risk tolerance.
        """
        bits = np.atleast_1d(np.asarray(hash_bits, dtype=float))
        hash_space_size = np.exp2(bits)
        log_term = np.log(1.0 - target_probability)
        return np.sqrt(-2.0 * hash_space_size * log_term)
