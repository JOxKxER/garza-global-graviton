"""FFT-based harmonic complexity filter for hallucination/EW-spoof detection.

Tactical use: legitimate physical/RF signals are described by a small number
of dominant harmonics; synthetic (AI-generated or spoofed) signals tend to
require many superimposed harmonics ("epicycles") to reproduce, mirroring
how Ptolemaic epicycle models needed ever more circles to fit orbits that a
simpler underlying model (Keplerian ellipses) explained directly.
"""

import numpy as np


class PtolemaicValidator:
    """Flags signals whose harmonic content is too complex to be organic."""

    def __init__(self, complexity_threshold=5, power_threshold=0.05):
        """Configure the max organic harmonic count and noise floor ratio."""
        self.complexity_threshold = complexity_threshold
        self.power_threshold = power_threshold

    def evaluate_signal(self, telemetry_signal, dt=0.01):
        """Decompose a signal via FFT and flag it if too many harmonics fit it.

        Tactical advantage: a vectorized O(N log N) spectral test that runs
        at edge-node speed to catch AI-hallucinated telemetry or electronic
        warfare spoofing before it reaches a fusion track.
        """
        N = len(telemetry_signal)
        # Perform Fast Fourier Transform.
        fft_values = np.fft.fft(telemetry_signal)
        frequencies = np.fft.fftfreq(N, d=dt)

        # Calculate Power Spectral Density.
        power = np.abs(fft_values) ** 2 / N
        max_power = np.max(power)

        # Count significant harmonics (epicycles).
        power_floor = self.power_threshold * max_power
        significant_harmonics = np.sum(power > power_floor)

        is_synthetic = significant_harmonics > self.complexity_threshold
        confidence = 1.0 - (
            self.complexity_threshold / max(significant_harmonics, 1)
        )

        return {
            "epicycle_count": significant_harmonics,
            "is_synthetic_spoof": is_synthetic,
            "confidence": confidence,
            "dominant_frequency_hz": frequencies[np.argmax(power)],
        }
