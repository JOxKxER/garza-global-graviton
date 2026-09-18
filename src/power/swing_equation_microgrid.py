"""Synchronous generator swing equation for microgrid frequency stability.

Tactical use: forward operating bases running autonomous drone charging
hubs and heavy hardware drivers off a microgrid can suffer frequency
collapse if a sudden load spike (a fleet beginning simultaneous fast
charging) isn't absorbed by generator inertia and damping fast enough.
The swing equation gives the exact frequency/angle response so a
controller can predict and pre-compensate for load transients.
"""

import numpy as np

NOMINAL_ANGULAR_FREQUENCY_RAD_S = 2.0 * np.pi * 60.0


class MicrogridSwingModel:
    """Simulates M*delta'' + D*delta' = Pm - Pe for batches of generators."""

    def step(
        self, rotor_angle, angular_velocity, inertia, damping,
        mechanical_power, electrical_power, time_step,
    ):
        """Advance rotor angle/velocity by one Euler swing-equation step.

        Tactical advantage: a single vectorized pass updates the full
        state of every generator on the microgrid at once, letting a
        controller simulate ahead of a scheduled load spike before it
        happens.
        """
        delta = np.atleast_1d(np.asarray(rotor_angle, dtype=float))
        omega = np.atleast_1d(np.asarray(angular_velocity, dtype=float))
        m = np.atleast_1d(np.asarray(inertia, dtype=float))
        d = np.atleast_1d(np.asarray(damping, dtype=float))
        p_mech = np.atleast_1d(np.asarray(mechanical_power, dtype=float))
        p_elec = np.atleast_1d(np.asarray(electrical_power, dtype=float))

        angular_acceleration = (p_mech - p_elec - d * omega) / m
        new_delta = delta + omega * time_step
        new_omega = omega + angular_acceleration * time_step
        return new_delta, new_omega

    def calc_frequency_deviation_hz(self, angular_velocity):
        """Convert rotor angular velocity deviation into a frequency-Hz offset.

        Tactical advantage: converts the raw state variable into the
        operator-meaningful "Hz off nominal" figure used for load-shed and
        protection-relay thresholds.
        """
        omega = np.atleast_1d(np.asarray(angular_velocity, dtype=float))
        return omega / (2.0 * np.pi)

    def is_within_stability_band(self, angular_velocity, max_deviation_hz=0.5):
        """Flag generators whose frequency deviation exceeds a safe band.

        Tactical advantage: a fast go/no-go check for whether a proposed
        load schedule keeps every generator within protection limits.
        """
        deviation_hz = self.calc_frequency_deviation_hz(angular_velocity)
        return np.abs(deviation_hz) <= max_deviation_hz
