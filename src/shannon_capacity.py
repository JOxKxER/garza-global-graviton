"""Shannon-Hartley channel capacity applied to jammed-link compression.

Covers the theoretical throughput ceiling under EW jamming noise.

Tactical use: derives the hard theoretical data-rate ceiling of a link under
a given signal-to-noise ratio (including hostile jamming noise), then works
backward to the compression ratio a payload needs to still fit that ceiling.
"""

import numpy as np


class ShannonCapacityPlanner:
    """Computes Shannon-Hartley channel capacity and required compression."""

    def __init__(self, bandwidth_hz):
        """Set the available channel bandwidth in Hz."""
        self.bandwidth_hz = bandwidth_hz

    def calc_channel_capacity(self, signal_power, noise_power):
        """Evaluate C = B * log2(1 + S/N), the max error-free bit rate.

        Tactical advantage: a closed-form ceiling on throughput under
        electronic warfare jamming, vectorized over arrays of S/N samples.
        """
        snr_linear = signal_power / noise_power
        return self.bandwidth_hz * np.log2(1.0 + snr_linear)

    def calc_required_compression(
        self, payload_bits_per_second, signal_power, noise_power
    ):
        """Compute the compression ratio needed to fit a payload under jamming.

        Tactical advantage: gives an edge encoder a direct target compression
        factor so telemetry keeps flowing even as jamming erodes the channel,
        instead of dropping packets once demand exceeds capacity.
        """
        capacity_bps = self.calc_channel_capacity(signal_power, noise_power)
        required_ratio = np.maximum(
            payload_bits_per_second / capacity_bps, 1.0
        )
        is_saturated = bool(np.any(payload_bits_per_second > capacity_bps))
        return {
            "channel_capacity_bps": capacity_bps,
            "required_compression_ratio": required_ratio,
            "link_saturated": is_saturated,
        }
