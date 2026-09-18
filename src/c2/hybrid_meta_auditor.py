"""Hybrid dual-trigger evaluator: the master supervisory audit loop.

Tactical use: a supervisory audit must fire on a deterministic heartbeat
(so it can never silently stop running) while also reacting instantly to
asynchronous danger signals -- an EW surprise spike or a collapsing
tactical efficiency -- without waiting for the next scheduled heartbeat
tick. Combining both into one OR condition guarantees no audit gap.
"""

import numpy as np

DEFAULT_HEARTBEAT_INTERVAL = 100
DEFAULT_SURPRISE_THRESHOLD = 10.0
DEFAULT_MIN_EFFICIENCY = 0.2


class HybridMetaAuditor:
    """Evaluates the combined heartbeat/surprise/efficiency trigger."""

    def __init__(
        self,
        heartbeat_interval=DEFAULT_HEARTBEAT_INTERVAL,
        surprise_threshold=DEFAULT_SURPRISE_THRESHOLD,
        min_efficiency=DEFAULT_MIN_EFFICIENCY,
    ):
        """Set the heartbeat period N, surprise threshold, efficiency floor."""
        self.heartbeat_interval = heartbeat_interval
        self.surprise_threshold = surprise_threshold
        self.min_efficiency = min_efficiency

    def evaluate_trigger(self, time_ticks, surprise_values, efficiency_values):
        """Evaluate Trig(t) = (t%N==0) OR (Omega_t>tau) OR (E_t<E_min).

        Tactical advantage: a single vectorized pass audits an entire
        stream of time ticks at once, identifying exactly which condition
        (or combination) fired at each tick for after-action review.
        """
        t = np.atleast_1d(np.asarray(time_ticks, dtype=np.int64))
        surprise = np.atleast_1d(np.asarray(surprise_values, dtype=float))
        efficiency = np.atleast_1d(np.asarray(efficiency_values, dtype=float))

        heartbeat_fired = (t % self.heartbeat_interval) == 0
        surprise_fired = surprise > self.surprise_threshold
        efficiency_fired = efficiency < self.min_efficiency

        triggered = heartbeat_fired | surprise_fired | efficiency_fired
        return {
            "triggered": triggered,
            "heartbeat_fired": heartbeat_fired,
            "surprise_fired": surprise_fired,
            "efficiency_fired": efficiency_fired,
            "trigger_count": int(np.sum(triggered)),
        }
