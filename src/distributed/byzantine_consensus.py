"""Byzantine Fault Tolerance viability check for degraded swarm/mesh nodes.

Tactical use: a sub-swarm or mesh partition can only reach a trustworthy
consensus decision (e.g. agreeing on a shared track picture or fire
authorization) if the number of jammed, destroyed, or compromised nodes f
stays within the classical bound n >= 3f + 1. This gives an instant
go/no-go on whether a degraded partition can still self-govern.
"""

import numpy as np


class ByzantineConsensusEvaluator:
    """Evaluates n >= 3f + 1 consensus viability for degraded node groups."""

    def calc_max_tolerable_faults(self, total_nodes):
        """Evaluate floor((n-1)/3), the max faulty nodes f consensus tolerates.

        Tactical advantage: vectorized over an array of candidate
        sub-swarm sizes, giving every partition its fault-tolerance budget
        in one call as the mesh reconfigures under attack.
        """
        n = np.atleast_1d(np.asarray(total_nodes, dtype=np.int64))
        return (n - 1) // 3

    def is_consensus_viable(self, total_nodes, faulty_nodes):
        """Evaluate whether n >= 3f + 1 holds for paired (n, f) arrays.

        Tactical advantage: a single vectorized pass screens an entire
        population of localized sub-swarm configurations for consensus
        viability, letting a C2 layer instantly identify which partitions
        can still be trusted to self-govern after losses.
        """
        n = np.atleast_1d(np.asarray(total_nodes, dtype=np.int64))
        f = np.atleast_1d(np.asarray(faulty_nodes, dtype=np.int64))
        return n >= (3 * f + 1)

    def calc_quorum_size(self, total_nodes):
        """Evaluate the minimum agreeing-node quorum floor((2n)/3) + 1.

        Tactical advantage: gives the exact vote count a partition needs
        before a consensus decision may be treated as binding.
        """
        n = np.atleast_1d(np.asarray(total_nodes, dtype=np.int64))
        return (2 * n) // 3 + 1
