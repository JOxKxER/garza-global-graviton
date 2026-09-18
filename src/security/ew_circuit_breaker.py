"""Shannon-surprise circuit breaker for contradictory sensor tripwires.

Tactical use: an EW spoofing attempt often injects telemetry that is
individually plausible but statistically inconsistent with the platform's
prior belief about its own state. Shannon surprise quantifies exactly how
inconsistent a new observation is with that prior; a circuit-breaker trip
on a surprise spike instantly quarantines the feed before it can corrupt
downstream fusion, without needing to identify the spoofing technique.
"""

import numpy as np

DEFAULT_SURPRISE_THRESHOLD = 10.0


class SpoofingCircuitBreaker:
    """Trips on statistically surprising telemetry vs. a prior belief."""

    def __init__(self, surprise_threshold=DEFAULT_SURPRISE_THRESHOLD):
        """Set the Shannon-surprise (nats) threshold that trips the breaker."""
        self.surprise_threshold = surprise_threshold

    def calc_shannon_surprise(self, observations, prior_mean, prior_std):
        """Evaluate Surprise = -ln P(observation | prior_belief).

        Models the prior belief as a Gaussian over expected sensor
        readings; an observation far in the tail of that distribution
        yields a large surprise value regardless of whether it is
        individually a "valid-looking" reading.

        Tactical advantage: a single vectorized pass scores an entire
        batch of incoming telemetry samples against the platform's prior
        state belief at once, with no per-sample loop.
        """
        x = np.atleast_1d(np.asarray(observations, dtype=float))
        mean = np.asarray(prior_mean, dtype=float)
        std = np.clip(np.asarray(prior_std, dtype=float), 1e-9, None)

        log_normalizer = np.log(std * np.sqrt(2.0 * np.pi))
        squared_deviation = 0.5 * ((x - mean) / std) ** 2
        return log_normalizer + squared_deviation

    def assess_circuit_breaker(self, observations, prior_mean, prior_std):
        """Flag observations whose surprise trips the quarantine threshold.

        Tactical advantage: gives an automated, instant quarantine
        decision per telemetry sample, isolating a spoofed feed before it
        reaches the core state estimator.
        """
        surprise = self.calc_shannon_surprise(
            observations, prior_mean, prior_std
        )
        tripped = surprise > self.surprise_threshold
        return {
            "surprise": surprise,
            "breaker_tripped": tripped,
            "quarantined_count": int(np.sum(tripped)),
        }
