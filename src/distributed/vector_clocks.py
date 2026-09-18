"""Vectorized vector-clock causality for clockless DDIL event ordering.

Tactical use: when GPS time sync is jammed, absolute timestamps cannot be
trusted to order events across a partitioned mesh. Vector clocks instead
establish a deterministic happened-before relation purely from each node's
locally incremented event counters, letting the mesh reconcile event order
correctly once connectivity is restored.
"""

import numpy as np

CONCURRENT = "CONCURRENT"
A_BEFORE_B = "A_HAPPENED_BEFORE_B"
B_BEFORE_A = "B_HAPPENED_BEFORE_A"
IDENTICAL = "IDENTICAL"


class VectorClockComparator:
    """Compares batches of paired vector clocks for causal ordering."""

    def compare(self, clocks_a, clocks_b):
        """Classify each paired (clock_a, clock_b) as before/after/concurrent.

        A happened-before B when every component of A is <= the
        corresponding component of B and at least one is strictly less
        (and symmetrically for B-before-A); otherwise the events are
        concurrent.

        Tactical advantage: a single vectorized comparison pass resolves
        causal order for an entire batch of event pairs collected across a
        partitioned mesh, with no per-pair loop and no shared clock.
        """
        a = np.atleast_2d(np.asarray(clocks_a, dtype=np.int64))
        b = np.atleast_2d(np.asarray(clocks_b, dtype=np.int64))

        a_leq_b = np.all(a <= b, axis=-1)
        b_leq_a = np.all(b <= a, axis=-1)
        identical = np.all(a == b, axis=-1)

        a_before_b = a_leq_b & ~identical
        b_before_a = b_leq_a & ~identical

        results = np.full(a.shape[0], CONCURRENT, dtype=object)
        results[identical] = IDENTICAL
        results[a_before_b] = A_BEFORE_B
        results[b_before_a] = B_BEFORE_A
        return results

    def merge(self, clocks_a, clocks_b):
        """Compute the componentwise-max merged clock for reconciling nodes.

        Tactical advantage: the standard vector-clock merge operation a
        rejoining node applies to fold a peer's observed event history
        into its own, without needing a synchronized wall clock.
        """
        a = np.atleast_2d(np.asarray(clocks_a, dtype=np.int64))
        b = np.atleast_2d(np.asarray(clocks_b, dtype=np.int64))
        return np.maximum(a, b)
