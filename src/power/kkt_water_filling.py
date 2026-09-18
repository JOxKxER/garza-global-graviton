"""KKT water-filling for optimal RF power allocation across noisy channels.

Tactical use: given a fixed total transmit power budget and channels with
different noise floors, uniformly splitting power wastes capacity on noisy
channels. The water-filling solution derived from the KKT conditions of
the channel-capacity maximization problem allocates more power to clean
channels and zero power to channels too noisy to be worth using.
"""

import numpy as np


class WaterFillingAllocator:
    """Solves batched KKT water-filling power allocation across channels."""

    def __init__(self, total_power_budget):
        """Set the total transmit power budget P available per agent."""
        self.total_power_budget = total_power_budget

    def allocate_power(self, noise_floors):
        """Solve p_i = max(0, mu - n_i) with sum(p_i) = P for each agent row.

        Finds the water level mu per row by testing every candidate active
        channel count k (sorted ascending by noise), then selecting the
        largest k whose implied mu still exceeds that channel's own noise
        floor -- the standard sorted-cumulative-sum water-filling solve.

        Tactical advantage: a single vectorized batch computes the optimal
        power allocation for an entire swarm's worth of agents at once,
        each with its own per-channel noise profile, with no per-agent
        Python loop.
        """
        noise = np.atleast_2d(np.asarray(noise_floors, dtype=float))
        num_channels = noise.shape[1]

        noise_sorted = np.sort(noise, axis=-1)
        cumulative_noise = np.cumsum(noise_sorted, axis=-1)
        channel_counts = np.arange(1, num_channels + 1)

        candidate_water_levels = (
            self.total_power_budget + cumulative_noise
        ) / channel_counts

        valid = noise_sorted <= candidate_water_levels
        best_k = np.max(
            np.where(valid, channel_counts, 0), axis=-1
        )
        best_k = np.clip(best_k, 1, num_channels)

        row_index = np.arange(noise.shape[0])
        water_level = candidate_water_levels[row_index, best_k - 1]

        allocation = np.maximum(water_level[:, None] - noise, 0.0)
        return {
            "allocation": allocation,
            "water_level": water_level,
        }

    def calc_channel_capacity(self, allocation, noise_floors):
        """Evaluate the Shannon capacity per channel under an allocation.

        Tactical advantage: verifies the allocation's payoff in bits/Hz per
        channel, letting a controller confirm the water-fill actually
        improved on a naive equal-power split.
        """
        noise = np.atleast_2d(np.asarray(noise_floors, dtype=float))
        return np.log2(1.0 + allocation / noise)
