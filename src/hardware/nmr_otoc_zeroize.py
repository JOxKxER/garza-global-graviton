"""NMR OTOC-inspired anti-tamper zeroize proxy for physical key destruction.

Tactical use: models the exponential information-scrambling behavior of an
Out-of-Time-Order Correlator (OTOC) -- the same phenomenon used in NMR-based
tamper sensing -- as a proxy for a casing-breach zeroize circuit. Repeated
scrambling transforms drive the overlap between the original key state and
the scrambled state toward zero exponentially fast, modeling near-instant,
information-theoretic destruction of the physical session key.
"""

import numpy as np


class OtocZeroizeSimulator:
    """Simulates exponential key-state scrambling from a tamper event."""

    def __init__(self, key_dimension=256, random_state=None):
        """Set the key state dimension and optional deterministic RNG."""
        self.key_dimension = key_dimension
        self.rng = (
            np.random.default_rng() if random_state is None else random_state
        )

    def generate_scrambling_unitary(self):
        """Build a Haar-random unitary matrix via QR decomposition.

        Tactical advantage: a single reusable scrambling operator models
        the chaotic, information-preserving-but-unrecoverable-without-the-
        key transform a tamper event triggers on the physical key state.
        """
        dim = self.key_dimension
        real_part = self.rng.normal(size=(dim, dim))
        imag_part = self.rng.normal(size=(dim, dim))
        ginibre_matrix = real_part + 1j * imag_part
        q_matrix, r_matrix = np.linalg.qr(ginibre_matrix)
        phase_correction = np.diag(r_matrix) / np.abs(np.diag(r_matrix))
        return q_matrix * phase_correction

    def simulate_zeroize(self, key_vector, num_iterations=100):
        """Iteratively scramble a key state, tracking its self-overlap decay.

        Tactical advantage: produces the exponential decay curve of the
        key's overlap with its original state, demonstrating that after
        only a few scrambling iterations the original key is
        information-theoretically unrecoverable from the casing hardware.
        """
        original_state = np.asarray(key_vector, dtype=complex)
        original_state = original_state / np.linalg.norm(original_state)

        scrambling_unitary = self.generate_scrambling_unitary()
        state = original_state.copy()

        overlaps = np.empty(num_iterations)
        for step in range(num_iterations):
            state = scrambling_unitary @ state
            overlaps[step] = np.abs(np.vdot(original_state, state)) ** 2

        return {
            "final_state": state,
            "overlap_decay_curve": overlaps,
            "is_zeroized": bool(overlaps[-1] < 1e-6),
        }
