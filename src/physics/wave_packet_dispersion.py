"""Quantum wave-packet dispersion: phase/group velocity and GVD spreading.

Tactical use: models phase velocity v_p versus group velocity v_g for a
free-particle dispersion relation, plus the resulting group-velocity
dispersion (GVD) growth of a Gaussian wave-packet's envelope over time --
used to bound the timing/throughput budget of an asynchronous edge data
pipeline whose signal envelope spreads as it propagates.
"""

from __future__ import annotations

import numpy as np


class WavePacketDispersion:
    """Computes phase velocity, group velocity, GVD, and envelope spreading."""

    def __init__(self, hbar: float = 1.0, mass: float = 1.0) -> None:
        """Set hbar and the particle mass (natural units by default)."""
        self.hbar = hbar
        self.mass = mass

    def calc_angular_frequency(self, wavenumber) -> np.ndarray:
        """Evaluate omega(k) = hbar*k^2 / (2*m), the free-particle relation.

        Tactical advantage: a single vectorized pass gives the carrier
        frequency for an entire array of wavenumbers making up a wave
        packet's spectral content.
        """
        k = np.atleast_1d(np.asarray(wavenumber, dtype=float))
        return (self.hbar * k ** 2) / (2.0 * self.mass)

    def calc_phase_velocity(
        self, wavenumber, angular_frequency: np.ndarray | None = None
    ) -> np.ndarray:
        """Evaluate v_p = omega / k for an array of wavenumbers.

        Tactical advantage: identifies how fast the carrier wave's crests
        move, independent of how fast the packet's energy/information
        envelope itself travels.
        """
        k = np.atleast_1d(np.asarray(wavenumber, dtype=float))
        omega = (
            self.calc_angular_frequency(k)
            if angular_frequency is None
            else np.atleast_1d(np.asarray(angular_frequency, dtype=float))
        )
        safe_k = np.where(k == 0.0, 1e-12, k)
        return omega / safe_k

    def calc_group_velocity(self, wavenumber) -> np.ndarray:
        """Evaluate v_g = d(omega)/dk = hbar*k/m for the free particle.

        Tactical advantage: the analytic derivative gives the exact
        envelope propagation speed with no finite-difference noise,
        vectorized across an entire wavenumber array.
        """
        k = np.atleast_1d(np.asarray(wavenumber, dtype=float))
        return (self.hbar * k) / self.mass

    def calc_group_velocity_numeric(
        self, wavenumber, angular_frequency
    ) -> np.ndarray:
        """Evaluate v_g via a numeric gradient for an arbitrary omega(k).

        Tactical advantage: works for any measured or non-analytic
        dispersion relation, not just the free-particle closed form,
        letting the same pipeline profile real hardware timing data.
        """
        k = np.atleast_1d(np.asarray(wavenumber, dtype=float))
        omega = np.atleast_1d(np.asarray(angular_frequency, dtype=float))
        return np.gradient(omega, k)

    def calc_group_velocity_dispersion(self, wavenumber) -> np.ndarray:
        """Evaluate GVD = d^2(omega)/dk^2 = hbar/m for the free particle.

        Tactical advantage: a constant GVD for the free-particle relation
        gives a closed-form envelope-spreading rate with no numerical
        second-derivative noise.
        """
        k = np.atleast_1d(np.asarray(wavenumber, dtype=float))
        return np.full_like(k, self.hbar / self.mass)

    def calc_envelope_spreading(
        self, initial_width: float, propagation_times
    ) -> np.ndarray:
        """Evaluate sigma(t) = sigma0*sqrt(1+(hbar*t/(2*m*sigma0^2))^2).

        The standard closed-form growth of a free Gaussian wave packet's
        position-space width under quadratic dispersion.

        Tactical advantage: a single vectorized pass forecasts, for an
        entire array of elapsed propagation times, exactly how much an
        edge pipeline's signal envelope will have spread -- and therefore
        how much timing margin a downstream stage must budget for.
        """
        if initial_width <= 0.0:
            raise ValueError("initial_width must be positive")
        t = np.atleast_1d(np.asarray(propagation_times, dtype=float))
        denom = 2.0 * self.mass * initial_width ** 2
        spread_factor = (self.hbar * t) / denom
        return initial_width * np.sqrt(1.0 + spread_factor ** 2)


if __name__ == "__main__":
    model = WavePacketDispersion(hbar=1.0, mass=1.0)
    wavenumbers = np.linspace(0.1, 5.0, 50)

    phase_velocity = model.calc_phase_velocity(wavenumbers)
    group_velocity = model.calc_group_velocity(wavenumbers)

    # Free-particle benchmark: v_g must equal exactly 2*v_p at every k.
    assert np.allclose(group_velocity, 2.0 * phase_velocity), (
        "Free-particle v_g = 2*v_p relation violated."
    )

    demo_omega = model.calc_angular_frequency(wavenumbers)
    numeric_group_velocity = model.calc_group_velocity_numeric(
        wavenumbers, demo_omega
    )
    # Central differences are exact for this quadratic omega(k); only the
    # array edges fall back to a less-accurate one-sided difference.
    assert np.allclose(
        numeric_group_velocity[1:-1], group_velocity[1:-1], atol=1e-8
    ), "Numeric group velocity gradient disagrees with the analytic form."

    gvd = model.calc_group_velocity_dispersion(wavenumbers)
    assert np.allclose(gvd, model.hbar / model.mass), "GVD must be constant."

    demo_times = np.array([0.0, 1.0, 10.0, 100.0])
    widths = model.calc_envelope_spreading(
        initial_width=1.0, propagation_times=demo_times
    )
    assert widths[0] == 1.0, "Envelope must start at its initial width."
    assert np.all(np.diff(widths) > 0.0), "Envelope must spread over time."

    print("WavePacketDispersion self-test passed.")
    print(f"v_p sample: {phase_velocity[:3]}")
    print(f"v_g sample: {group_velocity[:3]}")
    print(f"GVD (constant): {gvd[0]}")
    print(f"Envelope widths over time: {widths}")
