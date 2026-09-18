"""Newman's Modularity for identifying covert cells in adversarial networks.

Tactical use: intercepted adversarial RF/comms topology rarely reveals cell
structure directly. Modularity finds the community partition that most
exceeds what random connectivity alone would predict, exposing covert
cells; the nodes bridging multiple detected communities are the key
brokers whose removal would fragment the adversary's network.
"""

import numpy as np


class DarkNetworkAnalyzer:
    """Computes Newman's modularity and identifies inter-cell broker nodes."""

    def calc_modularity(self, adjacency_matrix, community_labels):
        """Evaluate Q = (1/2m) * sum((A_ij - k_i*k_j/2m) * delta(c_i,c_j)).

        Tactical advantage: a single vectorized pass scores an entire
        candidate community partition of an intercepted network topology
        at once, letting an analyst instantly compare partition hypotheses.
        """
        adjacency = np.asarray(adjacency_matrix, dtype=float)
        degrees = np.sum(adjacency, axis=-1)
        total_edge_weight = np.sum(adjacency) / 2.0
        if total_edge_weight == 0:
            return 0.0

        expected = np.outer(degrees, degrees) / (2.0 * total_edge_weight)
        labels = np.asarray(community_labels)
        same_community = (labels[:, None] == labels[None, :]).astype(float)

        return float(
            np.sum((adjacency - expected) * same_community)
            / (2.0 * total_edge_weight)
        )

    def calc_participation_coefficient(
        self, adjacency_matrix, community_labels
    ):
        """Evaluate P_i = 1 - sum_c (k_i,c / k_i)^2, the broker/bridge score.

        A node connected evenly across many communities scores near 1
        (a key broker); a node connected only within its own community
        scores near 0.

        Tactical advantage: a single vectorized pass ranks every
        intercepted node by how critical it is to inter-cell connectivity,
        directly prioritizing broker nodes for isolation.
        """
        adjacency = np.asarray(adjacency_matrix, dtype=float)
        labels = np.asarray(community_labels)
        unique_communities = np.unique(labels)

        degree = np.sum(adjacency, axis=-1)
        safe_degree = np.where(degree == 0, 1.0, degree)

        sum_of_squares = np.zeros_like(degree)
        for community in unique_communities:
            community_mask = (labels == community).astype(float)
            within_community_degree = adjacency @ community_mask
            sum_of_squares += (within_community_degree / safe_degree) ** 2

        return 1.0 - sum_of_squares
