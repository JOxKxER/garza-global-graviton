"""Relativistic gravimetric navigation via atomic clock frequency drift.

Tactical use: deep subsea or subterranean environments deny GPS and
external RF entirely. General relativity guarantees a clock's tick rate
depends on the local gravitational potential (gravitational time
dilation), so a precision atomic clock's frequency drift relative to a
reference clock directly encodes altitude/depth change -- a drift-free
absolute positioning channel that no jammer can spoof, because it isn't RF
at all.
"""

import numpy as np

SPEED_OF_LIGHT_M_S = 299_792_458.0
STANDARD_GRAVITY_M_S2 = 9.80665


class RelativisticGravimeter:
    """Converts atomic clock frequency drift into relative altitude/depth."""

    def __init__(
        self,
        local_gravity=STANDARD_GRAVITY_M_S2,
        speed_of_light=SPEED_OF_LIGHT_M_S,
    ):
        """Set the local gravitational acceleration g and speed of light c."""
        self.local_gravity = local_gravity
        self.speed_of_light = speed_of_light

    def calc_potential_difference(self, frequency_shift_ratio):
        """Evaluate Delta_Phi = (Delta_f / f) * c^2, the potential shift.

        Tactical advantage: converts a raw fractional clock-frequency
        measurement directly into a physical potential-energy quantity,
        vectorized across an entire stream of clock comparisons.
        """
        ratio = np.atleast_1d(np.asarray(frequency_shift_ratio, dtype=float))
        return ratio * (self.speed_of_light ** 2)

    def calc_relative_altitude(self, frequency_shift_ratio):
        """Evaluate Delta_h = Delta_Phi / g, the near-field altitude change.

        Tactical advantage: a single vectorized pass turns an entire
        stream of atomic clock readings into a dead-reckoning-free
        altitude/depth trace, immune to RF jamming or GPS denial.
        """
        potential_difference = self.calc_potential_difference(
            frequency_shift_ratio
        )
        return potential_difference / self.local_gravity

    def integrate_position_trace(
        self, frequency_shift_ratios, initial_altitude=0.0
    ):
        """Accumulate altitude changes into an absolute altitude trace.

        Tactical advantage: gives a continuously updating absolute
        position estimate for a platform operating with zero external
        navigation signal for an extended mission duration.
        """
        deltas = self.calc_relative_altitude(frequency_shift_ratios)
        return initial_altitude + np.cumsum(deltas)
