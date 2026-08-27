"""Deterministic entropy and fractal-scattering signal analysis."""

from __future__ import annotations

import math
from collections import Counter


class FractalSignalProcessor:
    """Measure information density and Menger-sponge volume decay."""

    @staticmethod
    def shannon_entropy(signal: str) -> float:
        if not signal:
            return 0.0
        length = len(signal)
        entropy = -sum(
            (count / length) * math.log2(count / length)
            for count in Counter(signal).values()
        )
        return round(entropy, 6)

    @staticmethod
    def scattering_volume(depth: int, base_volume: float = 1.0) -> float:
        if depth < 0:
            raise ValueError("depth cannot be negative")
        if base_volume < 0.0:
            raise ValueError("base_volume cannot be negative")
        return round(base_volume * (20.0 / 27.0) ** depth, 6)

    def analyze(self, signal: str, depth: int = 3) -> dict[str, object]:
        entropy = self.shannon_entropy(signal)
        return {
            "status": "success",
            "signal_length": len(signal),
            "entropy_bits": entropy,
            "fractal_depth": depth,
            "scattering_volume": self.scattering_volume(depth),
            "classification": (
                "high_density" if entropy > 3.8 else "stable_compressible"
            ),
        }
