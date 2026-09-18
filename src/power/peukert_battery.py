"""Peukert's Law battery endurance forecasting under dynamic load.

Tactical use: a drone's effective battery capacity shrinks nonlinearly as
discharge current rises (thermal and computational load spikes draw more
current than the rated value), so a linear "amp-hours remaining / current
draw" estimate overstates endurance. Peukert's Law captures that nonlinear
falloff so a swarm controller can forecast real time-to-depletion.
"""

import numpy as np

DEFAULT_PEUKERT_EXPONENT = 1.2


class PeukertBatteryModel:
    """Forecasts battery endurance using Peukert's Law under varying loads."""

    def __init__(
        self,
        rated_capacity_ah,
        rated_current_a=1.0,
        peukert_exponent=DEFAULT_PEUKERT_EXPONENT,
    ):
        """Set the rated capacity/current (nameplate test conditions) and k."""
        self.rated_capacity_ah = rated_capacity_ah
        self.rated_current_a = rated_current_a
        self.peukert_exponent = peukert_exponent

    def calc_peukert_capacity(self):
        """Evaluate C_p = C_rated * I_rated^(k-1), the normalized capacity.

        Tactical advantage: converts a nameplate amp-hour rating into the
        constant needed for the endurance formula, computed once per
        platform and reused across every load-forecast call.
        """
        return self.rated_capacity_ah * (
            self.rated_current_a ** (self.peukert_exponent - 1.0)
        )

    def calc_endurance_hours(self, discharge_current_a):
        """Evaluate t = C_p / I^k for an array of live discharge currents.

        Tactical advantage: a single vectorized call forecasts remaining
        flight time for an entire swarm, each drone under its own dynamic
        thermal/compute load, with no per-drone loop.
        """
        current = np.atleast_1d(np.asarray(discharge_current_a, dtype=float))
        peukert_capacity = self.calc_peukert_capacity()
        return peukert_capacity / (current ** self.peukert_exponent)

    def forecast_remaining_endurance(
        self, discharge_current_a, state_of_charge_fraction
    ):
        """Scale the Peukert endurance estimate by current state of charge.

        Tactical advantage: gives the swarm controller a mission-abort
        trigger -- remaining minutes on station -- that already accounts for
        both present battery depletion and present load intensity.
        """
        full_charge_hours = self.calc_endurance_hours(discharge_current_a)
        soc = np.atleast_1d(np.asarray(state_of_charge_fraction, dtype=float))
        return full_charge_hours * soc
