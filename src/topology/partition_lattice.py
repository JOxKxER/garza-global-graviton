"""Integer partition dominance lattice G_n for dependency-hierarchy indexing.

Tactical use: maps a module dependency hierarchy's branch-count shape
onto the corresponding integer partition of n, then indexes all
partitions of n as vertices of the classical dominance (majorization)
lattice. The lattice's covering relation (Hasse diagram edges) gives a
compact, mathematically well-defined "one step more/less concentrated"
transition graph between hierarchy shapes of equal total size.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def generate_partitions(n: int) -> list[tuple[int, ...]]:
    """Recursively generate every integer partition of n, largest part first.

    Tactical advantage: gives every possible dependency-hierarchy "shape
    signature" a canonical, enumerable representative, so two hierarchies
    with the same shape always map to the exact same partition.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return [()]

    def _partitions_with_max_part(
        remaining: int, max_part: int
    ) -> list[tuple[int, ...]]:
        if remaining == 0:
            return [()]
        results: list[tuple[int, ...]] = []
        for part in range(min(remaining, max_part), 0, -1):
            for rest in _partitions_with_max_part(remaining - part, part):
                results.append((part,) + rest)
        return results

    return _partitions_with_max_part(n, n)


def dominates(
    partition_a: tuple[int, ...], partition_b: tuple[int, ...]
) -> bool:
    """Evaluate the dominance (majorization) partial order A >= B.

    A dominates B iff, for every prefix length k, the sum of A's k
    largest parts is >= the sum of B's k largest parts (both padded
    with trailing zeros to equal length and equal total sum).

    Tactical advantage: the standard partial order used to build the
    integer-partition dominance lattice, giving a well-defined "more
    concentrated than" relation between two hierarchy shapes.
    """
    if sum(partition_a) != sum(partition_b):
        raise ValueError("dominance order requires equal-sum partitions")

    length = max(len(partition_a), len(partition_b))
    padded_a = list(partition_a) + [0] * (length - len(partition_a))
    padded_b = list(partition_b) + [0] * (length - len(partition_b))

    cumulative_a = 0
    cumulative_b = 0
    for value_a, value_b in zip(padded_a, padded_b):
        cumulative_a += value_a
        cumulative_b += value_b
        if cumulative_a < cumulative_b:
            return False
    return True


@dataclass
class PartitionLatticeNode:
    """A single vertex of the integer-partition dominance lattice G_n."""

    partition: tuple[int, ...]
    covers: list[tuple[int, ...]] = field(default_factory=list)


class PartitionLatticeIndex:
    """Builds and indexes the dominance lattice G_n over partitions of n."""

    def __init__(self, n: int) -> None:
        """Generate all partitions of n and build their dominance lattice."""
        if n < 0:
            raise ValueError("n must be non-negative")
        self.n = n
        self.partitions = generate_partitions(n)
        self._index = {
            partition: index
            for index, partition in enumerate(self.partitions)
        }
        self.nodes = self._build_lattice()

    def _build_lattice(
        self,
    ) -> dict[tuple[int, ...], PartitionLatticeNode]:
        """Build the Hasse diagram (covering relation) of the lattice.

        Tactical advantage: a single upfront pass over all partitions of
        n produces the exact covering edges needed for constant-time
        "next tier up" hierarchy-transition lookups later.
        """
        nodes = {
            partition: PartitionLatticeNode(partition)
            for partition in self.partitions
        }

        for candidate in self.partitions:
            dominators = [
                other
                for other in self.partitions
                if other != candidate and dominates(other, candidate)
            ]
            for dominator in dominators:
                is_covering = not any(
                    other != dominator
                    and other != candidate
                    and dominates(dominator, other)
                    and dominates(other, candidate)
                    for other in dominators
                )
                if is_covering:
                    nodes[dominator].covers.append(candidate)

        return nodes

    def rank_of(self, partition: tuple[int, ...]) -> int:
        """Return the partition's index within its generated ordering."""
        if partition not in self._index:
            raise KeyError(f"{partition} is not a partition of {self.n}")
        return self._index[partition]

    def map_hierarchy_to_partition(
        self, branch_counts: list[int]
    ) -> tuple[int, ...]:
        """Map a dependency-hierarchy's branch-count list to its partition.

        Tactical advantage: any two module dependency hierarchies with
        the same multiset of branch counts collapse onto the exact same
        lattice vertex, regardless of discovery order.
        """
        total = sum(branch_counts)
        if total != self.n:
            raise ValueError(f"branch_counts must sum to {self.n}")
        parts = [count for count in branch_counts if count > 0]
        return tuple(sorted(parts, reverse=True))


if __name__ == "__main__":
    lattice = PartitionLatticeIndex(n=6)

    all_partitions = set(lattice.partitions)
    assert (6,) in all_partitions
    assert (1, 1, 1, 1, 1, 1) in all_partitions
    assert len(lattice.partitions) == 11, "p(6) must equal 11."

    assert dominates((6,), (3, 3))
    assert dominates((3, 3), (1, 1, 1, 1, 1, 1))
    assert not dominates((3, 3), (4, 1, 1))
    assert not dominates((4, 1, 1), (3, 3))

    top_node = lattice.nodes[(6,)]
    assert (5, 1) in top_node.covers, "(6) must cover (5,1)."

    bottom_partition = (1, 1, 1, 1, 1, 1)
    assert lattice.rank_of((6,)) != lattice.rank_of(bottom_partition)

    mapped = lattice.map_hierarchy_to_partition([2, 1, 3, 0])
    assert mapped == (3, 2, 1), "Hierarchy-to-partition mapping incorrect."

    print("PartitionLatticeIndex self-test passed.")
    print(f"Partitions of {lattice.n}: {len(lattice.partitions)}")
    print(f"(6) covers: {top_node.covers}")
    print(f"Mapped hierarchy [2,1,3,0] -> {mapped}")
