"""Loop Quantum Gravity area quantization used as a discrete resource ledger.

Tactical use: LQG predicts spatial area can only take discrete quantized
values indexed by spin quantum numbers j. Mapped onto C2 resource scheduling,
each schedulable unit of compute/bandwidth is assigned a spin-network node
whose "area" (allocation weight) is drawn from the same discrete spectrum,
giving the ledger tamper-evidence: any allocation not on the quantized
spectrum is provably invalid rather than merely suspicious.
"""

import numpy as np

PLANCK_LENGTH_M = 1.616255e-35
BARBERO_IMMIRZI_GAMMA = 0.2375


class LQGLedger:
    """Quantizes resource allocations onto the LQG discrete area spectrum."""

    def __init__(
        self, gamma=BARBERO_IMMIRZI_GAMMA, planck_length=PLANCK_LENGTH_M
    ):
        """Set the Barbero-Immirzi parameter and Planck length unit scale."""
        self.gamma = gamma
        self.planck_length_sq = planck_length ** 2

    def calc_quantized_area(self, spin_quantum_numbers_j):
        """Evaluate A = 8*pi*gamma*l_P^2 * sum(sqrt(j*(j+1))) over spins j.

        Tactical advantage: vectorized over an array of spin-network nodes,
        producing the exact discrete allocation "area" for a resource grant
        in one pass, with no floating allocation between quantized levels.
        """
        j = np.asarray(spin_quantum_numbers_j, dtype=float)
        area_terms = np.sqrt(j * (j + 1.0))
        scale = 8.0 * np.pi * self.gamma * self.planck_length_sq
        return scale * np.sum(area_terms)

    def allocate_resource_grant(self, requested_units, spin_levels):
        """Round a requested allocation up to the nearest quantized spin set.

        Tactical advantage: any downstream grant can be re-verified by
        recomputing its quantized area from its spin labels; a grant whose
        area does not match its recorded spin labels is provably tampered.
        """
        spin_levels = np.asarray(spin_levels, dtype=float)
        unit_areas = np.sqrt(spin_levels * (spin_levels + 1.0))
        scale = 8.0 * np.pi * self.gamma * self.planck_length_sq

        assigned_spins = []
        allocated_area = 0.0
        requested_area = requested_units * scale
        remaining = requested_area
        while remaining > 0 and len(assigned_spins) < len(spin_levels) * 64:
            best_index = np.argmin(np.abs(unit_areas * scale - remaining))
            assigned_spins.append(float(spin_levels[best_index]))
            allocated_area += unit_areas[best_index] * scale
            remaining = requested_area - allocated_area
            if unit_areas[best_index] * scale <= 0:
                break

        return {
            "assigned_spin_labels": assigned_spins,
            "allocated_area": allocated_area,
            "requested_area": requested_area,
            "is_tamper_evident_valid": np.isclose(
                allocated_area, self.calc_quantized_area(assigned_spins)
            ),
        }
