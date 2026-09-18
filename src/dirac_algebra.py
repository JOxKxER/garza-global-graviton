"""Dirac/Pauli algebra primitives for 4-component spinor state tracking.

Tactical use: represents a two-band (chiral) sensor/track state as a single
bispinor so fused Left/Right channel data can be propagated and validated
with one vectorized linear-algebra object instead of two independent arrays.
"""

import numpy as np


class DiracAlgebra:
    """Builds the Pauli (2x2) and Dirac-representation gamma (4x4) matrices."""

    def __init__(self):
        """Precompute Pauli matrices and Dirac gamma matrices for reuse."""
        # Define 2x2 Pauli matrices.
        self.sigma_x = np.array([[0, 1], [1, 0]], dtype=complex)
        self.sigma_y = np.array([[0, -1j], [1j, 0]], dtype=complex)
        self.sigma_z = np.array([[1, 0], [0, -1]], dtype=complex)
        self.I2 = np.eye(2, dtype=complex)

        # Define 4x4 gamma matrices in the Dirac representation.
        zero = np.zeros((2, 2), dtype=complex)
        self.gamma_0 = np.block([[self.I2, zero], [zero, -self.I2]])
        self.gamma_1 = np.block([[zero, self.sigma_x], [-self.sigma_x, zero]])
        self.gamma_2 = np.block([[zero, self.sigma_y], [-self.sigma_y, zero]])
        self.gamma_3 = np.block([[zero, self.sigma_z], [-self.sigma_z, zero]])
        self.gamma_5 = (
            1j * self.gamma_0 @ self.gamma_1 @ self.gamma_2 @ self.gamma_3
        )

    def generate_bispinor(self, psi_L, psi_R):
        """Concatenate 2-component Left/Right chiral states into a bispinor.

        Tactical advantage: fuses two independent 2-channel readings into one
        object that the gamma matrices can act on directly, avoiding separate
        code paths per channel.
        """
        return np.concatenate((psi_L, psi_R))

    def check_invariants(self):
        """Verify {gamma_mu, gamma_nu} = 2*eta_munu*I and gamma_5 relations.

        Tactical advantage: a fast self-test that the matrix set is
        numerically well-formed before it is trusted in an edge pipeline.
        """
        gamma = (self.gamma_0, self.gamma_1, self.gamma_2, self.gamma_3)
        metric = np.diag([1, -1, -1, -1])
        identity = np.eye(4, dtype=complex)

        for mu, gamma_mu in enumerate(gamma):
            for nu, gamma_nu in enumerate(gamma):
                anticommutator = gamma_mu @ gamma_nu + gamma_nu @ gamma_mu
                expected = 2 * metric[mu, nu] * identity
                assert np.allclose(anticommutator, expected), (
                    f"Clifford relation failed for gamma_{mu}, gamma_{nu}"
                )

        assert np.allclose(self.gamma_5 @ self.gamma_5, identity), (
            "gamma_5 squared invariant failed"
        )
        for index, gamma_mu in enumerate(gamma):
            anticommutator = self.gamma_5 @ gamma_mu + gamma_mu @ self.gamma_5
            assert np.allclose(anticommutator, 0), (
                f"gamma_5 anticommutation failed for gamma_{index}"
            )

        return True
