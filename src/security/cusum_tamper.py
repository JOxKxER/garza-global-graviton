"""CUSUM change-point detection for slow, evasive sensor tamper attempts.

Tactical use: a spoofing or drift attack designed to stay under a hard
instantaneous threshold still accumulates a persistent bias over time.
CUSUM integrates that bias so a slow GPS spoof or IMU drift trips a flag
long before any single sample looks anomalous.
"""

import numpy as np


class CusumTamperDetector:
    """Computes one-sided CUSUM statistics for tamper/drift detection."""

    def __init__(self, target_mean=0.0, slack_k=0.5, alarm_threshold_h=5.0):
        """Set the expected in-control mean, slack k, and alarm threshold h."""
        self.target_mean = target_mean
        self.slack_k = slack_k
        self.alarm_threshold_h = alarm_threshold_h

    def calc_cusum_statistic(self, telemetry_signal):
        """Evaluate S_t = max(0, S_{t-1} + (x_t - mu0) - k) over a full series.

        Uses the identity S_t = C_t - min(C_0..C_t) where C_t is the
        cumulative sum of (x_t - mu0 - k) and C_0 = 0, which reproduces the
        reset-at-zero recursion without a per-sample Python loop.

        Tactical advantage: flags a slow-drift spoofing attempt against an
        entire telemetry buffer in one vectorized pass, suitable for
        continuous real-time ingestion at the edge.
        """
        deviations = telemetry_signal - self.target_mean - self.slack_k
        cumulative = np.concatenate(([0.0], np.cumsum(deviations)))
        running_min = np.minimum.accumulate(cumulative)
        cusum = cumulative - running_min
        return cusum[1:]

    def detect_tamper_events(self, telemetry_signal):
        """Flag sample indices where the CUSUM statistic exceeds threshold h.

        Tactical advantage: returns the exact onset index of a sustained
        drift, letting an operator distinguish a gradual spoof from normal
        sensor noise.
        """
        cusum = self.calc_cusum_statistic(telemetry_signal)
        alarmed = cusum > self.alarm_threshold_h
        return {
            "cusum_statistic": cusum,
            "alarmed_mask": alarmed,
            "first_alarm_index": (
                int(np.argmax(alarmed)) if np.any(alarmed) else -1
            ),
        }
