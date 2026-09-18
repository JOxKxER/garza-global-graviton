"""Hypercube LSH indexing: random-hyperplane projection + Hamming buckets.

Tactical use: extends the workspace's existing fixed-4D hypercube geometry
(`src.quaternion_engine.hypercube_vertices`) to an arbitrary k-bit
hypercube via locality-sensitive hashing (random hyperplane / SimHash
projection). Near-duplicate module feature vectors land on the same or a
nearby hypercube vertex, so duplicate/near-duplicate detection becomes an
O(1) bucket lookup plus a small Hamming-ball expansion instead of an O(n)
pairwise distance scan.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np

DEFAULT_NUM_BITS = 16


class HypercubeLSHIndex:
    """Projects feature vectors onto hypercube vertices and indexes them."""

    def __init__(
        self,
        feature_dim: int,
        num_bits: int = DEFAULT_NUM_BITS,
        random_state=None,
    ):
        """Set the input feature dimension and the hypercube's bit-width k."""
        if feature_dim <= 0:
            raise ValueError("feature_dim must be positive")
        if num_bits <= 0:
            raise ValueError("num_bits must be positive")

        rng = np.random.default_rng() if random_state is None else random_state
        self.feature_dim = feature_dim
        self.num_bits = num_bits
        self.hyperplanes = rng.normal(size=(num_bits, feature_dim))
        self._bit_weights = (2 ** np.arange(num_bits - 1, -1, -1)).astype(
            np.int64
        )
        self._buckets: dict[int, list] = {}

    def project_to_vertex(self, feature_vector) -> int:
        """Project one feature vector onto its k-bit hypercube vertex id.

        Tactical advantage: a single matrix-vector product plus a sign
        threshold maps an arbitrary-dimension feature vector onto a
        compact integer id, ready for O(1) bucket lookup.
        """
        vector = np.atleast_1d(np.asarray(feature_vector, dtype=float))
        if vector.shape[-1] != self.feature_dim:
            raise ValueError(
                f"feature_vector must have dimension {self.feature_dim}"
            )
        projections = self.hyperplanes @ vector
        bits = (projections >= 0.0).astype(np.int64)
        return int(np.dot(bits, self._bit_weights))

    def project_batch_to_vertices(self, feature_matrix) -> np.ndarray:
        """Project a batch of feature vectors onto hypercube vertex ids.

        Tactical advantage: a single vectorized pass hashes an entire
        batch of module feature vectors at once, with no per-item loop.
        """
        matrix = np.atleast_2d(np.asarray(feature_matrix, dtype=float))
        if matrix.shape[-1] != self.feature_dim:
            raise ValueError(
                f"feature_matrix must have dimension {self.feature_dim}"
            )
        projections = matrix @ self.hyperplanes.T
        bits = (projections >= 0.0).astype(np.int64)
        return bits @ self._bit_weights

    def vertex_to_hypercube_coordinates(self, vertex_id: int) -> np.ndarray:
        """Map a k-bit vertex id to its {-1, +1}^k hypercube corner.

        Uses the same +/-1 sign convention as
        `src.quaternion_engine.hypercube_vertices`, generalized from a
        fixed 4 dimensions to this index's configured bit-width k.
        """
        if not 0 <= vertex_id < (1 << self.num_bits):
            raise ValueError("vertex_id out of range for this index")
        bits = np.array(
            [
                (vertex_id >> shift) & 1
                for shift in range(self.num_bits - 1, -1, -1)
            ]
        )
        return np.where(bits == 1, 1.0, -1.0)

    def register(self, item_id, feature_vector) -> int:
        """Register an item's feature vector and return its bucket vertex id.

        Tactical advantage: registration and lookup share the same
        projection, so a newly registered module is immediately
        discoverable by any subsequent near-duplicate query.
        """
        vertex_id = self.project_to_vertex(feature_vector)
        self._buckets.setdefault(vertex_id, []).append(item_id)
        return vertex_id

    @staticmethod
    def hamming_distance(vertex_a: int, vertex_b: int) -> int:
        """Compute the bit-flip (Hamming) distance between two vertex ids."""
        return bin(vertex_a ^ vertex_b).count("1")

    def query_candidates(
        self, feature_vector, max_hamming_distance: int = 0
    ) -> list:
        """Return registered item ids within a Hamming ball of the query.

        Expands the search from the exact bucket (radius 0) outward by
        flipping every combination of up to `max_hamming_distance` bits,
        the standard multi-probe LSH technique for recovering
        near-duplicates that landed one or two bit-flips away from the
        query's own vertex.

        Tactical advantage: near-duplicate modules that differ by only a
        few noisy features are still found, without falling back to a
        full linear scan of every registered item.
        """
        if max_hamming_distance < 0:
            raise ValueError("max_hamming_distance must be non-negative")

        query_vertex = self.project_to_vertex(feature_vector)
        seen_vertices: set[int] = set()
        candidates: list = []

        for radius in range(max_hamming_distance + 1):
            for flip_positions in combinations(range(self.num_bits), radius):
                neighbor_vertex = query_vertex
                for position in flip_positions:
                    neighbor_vertex ^= 1 << (self.num_bits - 1 - position)
                if neighbor_vertex in seen_vertices:
                    continue
                seen_vertices.add(neighbor_vertex)
                candidates.extend(self._buckets.get(neighbor_vertex, []))
        return candidates


if __name__ == "__main__":
    import sys
    from pathlib import Path

    _repo_root = str(Path(__file__).resolve().parents[2])
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)

    from src.quaternion_engine import hypercube_vertices

    reference_vertices = hypercube_vertices(half_extent=1.0)
    assert reference_vertices.shape == (16, 4), "Reference hypercube changed."

    demo_rng = np.random.default_rng(7)
    index = HypercubeLSHIndex(
        feature_dim=8, num_bits=12, random_state=demo_rng
    )

    base_vector = np.random.default_rng(1).normal(size=8)
    near_duplicate = base_vector + np.random.default_rng(2).normal(
        scale=0.01, size=8
    )
    unrelated_vector = np.random.default_rng(3).normal(size=8) * 10.0

    vertex_base = index.register("module_a_v1", base_vector)
    vertex_unrelated = index.register("module_b", unrelated_vector)

    exact_hits = index.query_candidates(base_vector, max_hamming_distance=0)
    assert "module_a_v1" in exact_hits, "Exact bucket lookup failed."

    expanded_hits = index.query_candidates(
        near_duplicate, max_hamming_distance=3
    )
    assert "module_a_v1" in expanded_hits, (
        "Near-duplicate not found within Hamming radius 3."
    )

    coordinates = index.vertex_to_hypercube_coordinates(vertex_base)
    assert set(np.unique(coordinates)).issubset({-1.0, 1.0})

    distance = HypercubeLSHIndex.hamming_distance(
        vertex_base, vertex_unrelated
    )
    print("HypercubeLSHIndex self-test passed.")
    print(f"Base vertex: {vertex_base}, unrelated vertex: {vertex_unrelated}")
    print(f"Hamming distance (unrelated pair): {distance}")
    print(f"Near-duplicate recovered via expanded probe: {expanded_hits}")
