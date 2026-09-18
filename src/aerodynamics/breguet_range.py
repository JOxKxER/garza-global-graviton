"""Breguet Range Equation for dynamic fuel-endurance optimization.

Tactical use: recomputes achievable range/endurance in real time as
atmospheric drag (L/D) and airspeed change during flight, letting a
UAV/hypersonic asset re-plan its mission radius instead of relying on a
static pre-flight range figure.
"""

import numpy as np


class BreguetRangeCalculator:
    """Computes Breguet range for arrays of live flight profiles."""

    def calc_range(
        self,
        velocity,
        specific_fuel_consumption,
        lift_to_drag_ratio,
        initial_weight,
        final_weight,
    ):
        """Evaluate R = (v/c) * (L/D) * ln(W0/W1) over an array of profiles.

        Tactical advantage: a single vectorized pass re-evaluates range for
        an entire fleet as each asset's live velocity, fuel burn, and drag
        state diverge, with no per-aircraft loop.
        """
        v = np.atleast_1d(np.asarray(velocity, dtype=float))
        c = np.atleast_1d(np.asarray(specific_fuel_consumption, dtype=float))
        ld_ratio = np.atleast_1d(
            np.asarray(lift_to_drag_ratio, dtype=float)
        )
        w0 = np.atleast_1d(np.asarray(initial_weight, dtype=float))
        w1 = np.atleast_1d(np.asarray(final_weight, dtype=float))

        weight_ratio = np.log(w0 / w1)
        return (v / c) * ld_ratio * weight_ratio

    def calc_max_endurance_weight(
        self, range_target, velocity, specific_fuel_consumption,
        lift_to_drag_ratio, initial_weight,
    ):
        """Solve for the final weight W1 needed to hit a required range.

        Tactical advantage: inverts the range equation so a mission planner
        can ask "how much fuel must remain unburned to still reach the
        target" instead of only forward-predicting range from fuel state.
        """
        v = np.atleast_1d(np.asarray(velocity, dtype=float))
        c = np.atleast_1d(np.asarray(specific_fuel_consumption, dtype=float))
        ld_ratio = np.atleast_1d(
            np.asarray(lift_to_drag_ratio, dtype=float)
        )
        w0 = np.atleast_1d(np.asarray(initial_weight, dtype=float))

        exponent = range_target / ((v / c) * ld_ratio)
        return w0 / np.exp(exponent)
