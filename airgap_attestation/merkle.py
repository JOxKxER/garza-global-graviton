"""Domain-separated Merkle tree used to bind every recorded execution event
into a single tamper-evident root hash.

Design notes (why this differs from a naive "hash pairs, duplicate the odd
node" tree):

* Leaf and internal nodes are hashed with distinct one-byte domain prefixes
  (0x00 for leaves, 0x01 for internal nodes). Without this separation an
  attacker can present an internal node as if it were a leaf (or vice versa)
  and forge a valid-looking proof for data that was never recorded -- this is
  the classic second-preimage weakness in "textbook" Merkle trees (the same
  class of bug behind CVE-2012-2459 in early Bitcoin SPV clients).
* An odd trailing node is promoted unchanged to the next level instead of
  being duplicated against itself. Duplicating the last node makes two
  different leaf sets (one with N leaves, one with N+1 duplicating the last)
  produce the same root, which breaks the "one root <-> one exact leaf set"
  property this protocol relies on.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import List, Sequence, Tuple

_LEAF_PREFIX = b"\x00"
_NODE_PREFIX = b"\x01"


def _sha256(*parts: bytes) -> bytes:
    h = hashlib.sha256()
    for part in parts:
        h.update(part)
    return h.digest()


def leaf_hash(data: bytes) -> bytes:
    return _sha256(_LEAF_PREFIX, data)


def node_hash(left: bytes, right: bytes) -> bytes:
    return _sha256(_NODE_PREFIX, left, right)


@dataclass(frozen=True)
class MerkleProofStep:
    sibling: bytes
    sibling_is_right: bool  # True if the sibling sits to the right of our node


class MerkleTree:
    """An immutable Merkle tree built once from an ordered list of leaves."""

    def __init__(self, leaves: Sequence[bytes]):
        if not leaves:
            raise ValueError("MerkleTree requires at least one leaf")
        self._leaf_count = len(leaves)
        self._levels: List[List[bytes]] = [[leaf_hash(item) for item in leaves]]
        while len(self._levels[-1]) > 1:
            self._levels.append(self._build_next_level(self._levels[-1]))

    @staticmethod
    def _build_next_level(level: List[bytes]) -> List[bytes]:
        next_level: List[bytes] = []
        for i in range(0, len(level), 2):
            if i + 1 < len(level):
                next_level.append(node_hash(level[i], level[i + 1]))
            else:
                next_level.append(level[i])  # promote lone node, never duplicate
        return next_level

    @property
    def root(self) -> bytes:
        return self._levels[-1][0]

    @property
    def leaf_count(self) -> int:
        return self._leaf_count

    def proof(self, index: int) -> List[MerkleProofStep]:
        if not 0 <= index < self._leaf_count:
            raise IndexError("leaf index out of range")
        steps: List[MerkleProofStep] = []
        idx = index
        for level in self._levels[:-1]:
            is_right_node = idx % 2 == 1
            sibling_idx = idx - 1 if is_right_node else idx + 1
            if sibling_idx < len(level):
                steps.append(
                    MerkleProofStep(
                        sibling=level[sibling_idx],
                        sibling_is_right=not is_right_node,
                    )
                )
            # else: idx was the lone promoted node at this level, no sibling step
            idx //= 2
        return steps

    @staticmethod
    def verify_proof(
        leaf_data: bytes,
        proof: Sequence[MerkleProofStep],
        expected_root: bytes,
    ) -> bool:
        current = leaf_hash(leaf_data)
        for step in proof:
            if step.sibling_is_right:
                current = node_hash(current, step.sibling)
            else:
                current = node_hash(step.sibling, current)
        return current == expected_root


def encode_proof(proof: Sequence[MerkleProofStep]) -> List[Tuple[str, str]]:
    """JSON-friendly encoding: (hex_sibling, 'L'|'R')."""
    return [(step.sibling.hex(), "R" if step.sibling_is_right else "L") for step in proof]


def decode_proof(encoded: Sequence[Tuple[str, str]]) -> List[MerkleProofStep]:
    return [MerkleProofStep(bytes.fromhex(h), side == "R") for h, side in encoded]
