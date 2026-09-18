"""Differential privacy Gaussian mechanism for telemetry anonymization.

Tactical use: raw per-agent telemetry (exact position, exact fuel state)
can be exploited by adversarial traffic analysis to deanonymize or target
individual platforms. The Gaussian mechanism adds calibrated noise scaled
to the query's sensitivity and the desired (epsilon, delta) privacy budget,
obscuring individual readings while preserving accurate aggregate/global
swarm metrics for the commander.
"""

import numpy as np


class GaussianPrivacyMechanism:
    """Applies (epsilon, delta)-calibrated Gaussian noise to telemetry."""

    def __init__(self, epsilon, delta, sensitivity):
        """Set the privacy budget (epsilon, delta) and sensitivity delta_f."""
        self.epsilon = epsilon
        self.delta = delta
        self.sensitivity = sensitivity

    def calc_noise_scale(self):
        """Evaluate sigma >= (delta_f * sqrt(2*ln(1.25/delta))) / epsilon.

        Tactical advantage: derives the minimum noise standard deviation
        that provably satisfies the requested privacy guarantee, so the
        obfuscation is neither wastefully strong nor unsafely weak.
        """
        return (
            self.sensitivity * np.sqrt(2.0 * np.log(1.25 / self.delta))
        ) / self.epsilon

    def privatize(self, raw_values, random_state=None):
        """Apply M(x) = f(x) + N(0, sigma^2) to an array of raw readings.

        Tactical advantage: a single vectorized noise-injection pass
        anonymizes an entire batch of live telemetry readings at once,
        suitable for continuous streaming obfuscation at the edge.
        """
        rng = np.random.default_rng() if random_state is None else random_state
        values = np.atleast_1d(np.asarray(raw_values, dtype=float))
        noise = rng.normal(0.0, self.calc_noise_scale(), size=values.shape)
        return values + noise

    def calc_expected_utility_loss(self):
        """Evaluate E[|noise|] = sigma * sqrt(2/pi), the mean absolute error.

        Tactical advantage: gives a commander a concrete accuracy-cost
        figure for the chosen privacy budget, before it is applied.
        """
        return self.calc_noise_scale() * np.sqrt(2.0 / np.pi)
