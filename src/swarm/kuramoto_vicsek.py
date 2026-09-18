"""Kuramoto-Vicsek coupled oscillator model for leaderless swarm coherence.

Tactical use: synchronizes both sensor sampling phase and platform heading
across a swarm using only local pairwise coupling -- no central leader
node broadcasts a reference signal, so the swarm keeps synchronizing even
if any subset of nodes is jammed, destroyed, or partitioned away.
"""

import numpy as np


class KuramotoVicsekModel:
    """Simulates coupled phase/heading synchronization across a swarm."""

    def __init__(self, coupling_strength=1.0):
        """Set the global coupling strength K scaling neighbor influence."""
        self.coupling_strength = coupling_strength

    def calc_phase_derivative(
        self, phases, natural_frequencies, coupling_matrix=None
    ):
        """Evaluate dtheta_i/dt = omega_i + (K/N)*sum_j W_ij*sin(dtheta).

        Tactical advantage: a single vectorized pairwise-phase-difference
        pass computes every agent's synchronization drive at once, scaling
        to large swarms without a per-agent-pair loop.
        """
        theta = np.atleast_1d(np.asarray(phases, dtype=float))
        omega = np.atleast_1d(np.asarray(natural_frequencies, dtype=float))
        num_agents = theta.shape[0]

        weights = (
            np.ones((num_agents, num_agents))
            if coupling_matrix is None
            else np.asarray(coupling_matrix, dtype=float)
        )

        phase_diff = theta[None, :] - theta[:, None]
        coupling_term = (self.coupling_strength / num_agents) * np.sum(
            weights * np.sin(phase_diff), axis=1
        )
        return omega + coupling_term

    def step(
        self, phases, natural_frequencies, time_step, coupling_matrix=None
    ):
        """Advance all phases/headings by one Euler integration time step.

        Tactical advantage: a ready-to-use per-tick update for an entire
        swarm's heading/phase state, suitable for a real-time flight
        control or sensor-scheduling loop.
        """
        phase_dot = self.calc_phase_derivative(
            phases, natural_frequencies, coupling_matrix
        )
        theta = np.atleast_1d(np.asarray(phases, dtype=float))
        return theta + phase_dot * time_step

    def calc_order_parameter(self, phases):
        """Evaluate the Kuramoto order parameter r*e^(i*psi).

        Tactical advantage: a single scalar r in [0, 1] quantifying how
        tightly synchronized the swarm currently is, with r near 1
        indicating full phase/heading lock-in.
        """
        theta = np.atleast_1d(np.asarray(phases, dtype=float))
        complex_mean = np.mean(np.exp(1j * theta))
        return {
            "synchronization_r": float(np.abs(complex_mean)),
            "mean_phase_psi": float(np.angle(complex_mean)),
        }
