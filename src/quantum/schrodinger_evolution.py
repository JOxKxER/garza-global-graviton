"""Unitary Schrodinger time evolution for onboard QND magnetometer emulation.

Tactical use: a Quantum Non-Demolition (QND) magnetometer's qubit-like
sensing element must be propagated forward via unitary time evolution
between measurements; precomputing one evolution operator and applying it
to a batch of independent sensor-node states lets an edge processor
emulate an entire QND sensor array in one matrix multiply.
"""

import numpy as np
from scipy.linalg import expm

REDUCED_PLANCK_NATURAL_UNITS = 1.0


class SchrodingerEvolver:
    """Evolves batches of qubit wavefunctions under a fixed Hamiltonian."""

    def __init__(self, hamiltonian, hbar=REDUCED_PLANCK_NATURAL_UNITS):
        """Set the 2x2 Hamiltonian matrix and hbar (natural units default)."""
        self.hamiltonian = np.asarray(hamiltonian, dtype=complex)
        self.hbar = hbar

    def calc_evolution_operator(self, time_step):
        """Evaluate U(t) = exp(-i*H*t/hbar), the unitary propagator.

        Tactical advantage: computed once per time step regardless of how
        many parallel sensor states are being tracked, since the operator
        depends only on the (fixed) Hamiltonian and elapsed time.
        """
        exponent = -1j * self.hamiltonian * time_step / self.hbar
        return expm(exponent)

    def evolve_states(self, initial_states, time_step):
        """Propagate a batch of qubit states psi(0) forward to psi(t).

        Tactical advantage: a single matrix multiply advances every
        emulated QND sensor node's state at once, letting a swarm-wide
        magnetometer array be time-stepped without a per-node loop.
        """
        evolution_operator = self.calc_evolution_operator(time_step)
        states = np.atleast_2d(np.asarray(initial_states, dtype=complex))
        return np.einsum("ij,nj->ni", evolution_operator, states)

    def calc_measurement_probabilities(self, states):
        """Compute Born-rule probabilities |psi_i|^2 for each basis state.

        Tactical advantage: converts the evolved complex amplitudes into
        the observable readout probabilities a QND measurement would
        report, for an entire batch of sensor nodes at once.
        """
        states = np.atleast_2d(np.asarray(states, dtype=complex))
        return np.abs(states) ** 2
