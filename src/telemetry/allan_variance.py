"""Allan Variance analysis for real-time IMU drift characterization.

Tactical use: when GPS is jammed or spoofed, a platform must dead-reckon on
IMU data alone. Allan variance quantifies how an IMU's error grows with
integration time tau, letting a navigation filter set drift-rate-aware
uncertainty bounds instead of assuming a fixed noise model that becomes
wrong the longer GPS stays denied.
"""

import numpy as np


class AllanVarianceAnalyzer:
    """Computes Allan variance/deviation curves from IMU sample streams."""

    def __init__(self, sample_rate_hz):
        """Set the IMU sampling rate used to convert cluster size to tau."""
        self.sample_rate_hz = sample_rate_hz

    def calc_allan_variance(self, imu_samples, cluster_sizes):
        """Evaluate sigma^2(tau) for each requested averaging cluster size m.

        For each m, computes cluster (bin) averages of the input stream via
        a reshape (no per-sample loop), then sigma^2(tau) = 0.5 * mean of
        the squared difference between consecutive cluster averages. Only
        the small outer set of requested cluster sizes is iterated, not the
        underlying sample stream.

        Tactical advantage: gives a navigation filter the full drift-vs-time
        curve for an IMU noise buffer in one profiling pass, identifying the
        integration time at which dead-reckoning error grows fastest.
        """
        samples = np.asarray(imu_samples, dtype=float)
        num_samples = samples.shape[0]

        tau_values = []
        allan_variances = []
        for cluster_size in cluster_sizes:
            usable_length = (num_samples // cluster_size) * cluster_size
            if usable_length < 2 * cluster_size:
                continue
            clusters = samples[:usable_length].reshape(-1, cluster_size)
            cluster_means = np.mean(clusters, axis=1)
            diffs = np.diff(cluster_means)
            variance = 0.5 * np.mean(diffs ** 2)

            tau_values.append(cluster_size / self.sample_rate_hz)
            allan_variances.append(variance)

        tau_values = np.array(tau_values)
        allan_variances = np.array(allan_variances)
        return {
            "tau": tau_values,
            "allan_variance": allan_variances,
            "allan_deviation": np.sqrt(allan_variances),
        }
