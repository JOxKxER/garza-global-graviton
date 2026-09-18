"""Pancharatnam-Berry geometric phase via discrete Wilson-loop transport.

Tactical use: tracks the gauge-invariant geometric phase accumulated by a
quantum (or classical adiabatic) state carried around a closed loop in
parameter space. Because the Wilson-loop product of consecutive-state
overlaps is invariant under each sampled state's arbitrary local phase
choice, the resulting phase is topologically protected against the kind
of per-sample phase jitter that would corrupt a naive running-phase
tracker.
"""

from __future__ import annotations

import numpy as np


class PancharatnamBerryPhase:
    """Computes geometric phase from a closed loop of quantum state samples."""

    @staticmethod
    def _normalize(states: np.ndarray) -> np.ndarray:
        """L2-normalize each state vector (row) in a batch."""
        norms = np.linalg.norm(states, axis=-1, keepdims=True)
        safe_norms = np.where(norms == 0.0, 1.0, norms)
        return states / safe_norms

    @staticmethod
    def calc_overlap(state_a, state_b) -> complex:
        """Evaluate the inner product <a|b> for two complex state vectors."""
        return complex(np.vdot(state_a, state_b))

    @classmethod
    def calc_wilson_loop_phase(cls, state_sequence) -> float:
        """Evaluate gamma = -Im(log(prod <psi_i|psi_{i+1}>)) around a loop.

        The product runs over every consecutive pair in the sequence,
        including the closing link from the last sample back to the
        first, treating the sequence as one full adiabatic cycle.

        Tactical advantage: gauge-invariant and topologically protected
        -- small numerical or hardware phase jitter in any one sampled
        state barely perturbs the accumulated loop phase, unlike
        phase-tracking each state independently.
        """
        states = cls._normalize(np.asarray(state_sequence, dtype=complex))
        num_points = states.shape[0]

        wilson_product = complex(1.0, 0.0)
        for index in range(num_points):
            next_state = states[(index + 1) % num_points]
            wilson_product *= cls.calc_overlap(states[index], next_state)

        return float(-np.angle(wilson_product))

    @classmethod
    def parallel_transport_loop(cls, state_sequence):
        """Explicitly parallel-transport a state sequence around a loop.

        Rephases each state (after the first) so its overlap with the
        previous transported state is real and positive -- the discrete
        parallel-transport gauge condition -- then returns both the
        transported sequence and the residual closing-loop phase
        mismatch, which equals the Berry phase.

        Tactical advantage: an independent, explicit integration of the
        same geometric phase the Wilson-loop shortcut computes, letting
        the two methods cross-validate each other.
        """
        states = cls._normalize(np.asarray(state_sequence, dtype=complex))
        num_points = states.shape[0]

        transported = [states[0]]
        for index in range(1, num_points):
            previous_state = transported[-1]
            current_state = states[index]
            overlap = cls.calc_overlap(previous_state, current_state)
            rephasing = np.exp(-1j * np.angle(overlap))
            transported.append(current_state * rephasing)

        closing_overlap = cls.calc_overlap(transported[-1], transported[0])
        berry_phase = float(-np.angle(closing_overlap))
        return np.array(transported), berry_phase


def _spin_half_coherent_state(
    polar_angle: float, azimuth: float
) -> np.ndarray:
    """Build a spin-1/2 coherent state |psi(theta, phi)> on the Bloch sphere.

    Kept as a module-level helper since it is only used by the self-test.
    """
    return np.array(
        [
            np.cos(polar_angle / 2.0),
            np.exp(1j * azimuth) * np.sin(polar_angle / 2.0),
        ],
        dtype=complex,
    )


if __name__ == "__main__":
    demo_polar_angle = np.pi / 3.0
    demo_num_points = 400
    azimuths = np.linspace(
        0.0, 2.0 * np.pi, demo_num_points, endpoint=False
    )

    loop_states = np.array(
        [
            _spin_half_coherent_state(demo_polar_angle, phi)
            for phi in azimuths
        ]
    )

    wilson_phase = PancharatnamBerryPhase.calc_wilson_loop_phase(loop_states)
    _, transported_phase = PancharatnamBerryPhase.parallel_transport_loop(
        loop_states
    )

    # Analytic spin-1/2 result: gamma = -pi * (1 - cos(theta)).
    expected_phase = -np.pi * (1.0 - np.cos(demo_polar_angle))

    assert abs(wilson_phase - expected_phase) < 1e-2, (
        "Wilson-loop phase disagrees with the analytic spin-1/2 result."
    )
    assert abs(wilson_phase - transported_phase) < 1e-6, (
        "Wilson-loop and parallel-transport phases must agree."
    )

    print("PancharatnamBerryPhase self-test passed.")
    print(f"Wilson-loop phase: {wilson_phase:.6f} rad")
    print(f"Parallel-transport phase: {transported_phase:.6f} rad")
    print(f"Analytic expected phase: {expected_phase:.6f} rad")
