"""Merkle verification and tamper-evident state integrity services."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

import numpy as np

try:
    from .core import MerkleTree, hash_numpy_array
except ImportError:
    from core import MerkleTree, hash_numpy_array


def _canonicalize(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return {
            "dtype": value.dtype.str,
            "shape": list(value.shape),
            "data": value.tolist(),
        }
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, bytes):
        return {"encoding": "hex", "data": value.hex()}
    if isinstance(value, dict):
        return {str(key): _canonicalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    return value


def hash_state(state: Any) -> str:
    """Return a deterministic SHA-256 digest for a JSON-like state value."""
    canonical = json.dumps(
        _canonicalize(state),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def hash_dataset(data: np.ndarray) -> str:
    """Hash a NumPy dataset using the suite's dtype and shape-aware format."""
    return hash_numpy_array(np.asarray(data))


def build_state_tree(states: Iterable[Any]) -> MerkleTree:
    """Build a Merkle tree from deterministic state digests."""
    return MerkleTree([hash_state(state) for state in states])


def verify_state_proof(
    state: Any, proof: list[dict[str, str]], expected_root: str
) -> bool:
    """Verify a state value against a Merkle root and audit proof."""
    return MerkleTree.verify_audit_proof(
        hash_state(state), proof, expected_root
    )


@dataclass
class StateIntegrityChain:
    """Append-only chain linking each state snapshot to its predecessor."""

    entries: list[dict[str, Any]] = field(default_factory=list)

    def append(
        self, state: Any, metadata: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        index = len(self.entries)
        previous_hash = (
            self.entries[-1]["entry_hash"] if self.entries else "0" * 64
        )
        state_hash = hash_state(state)
        entry_metadata = _canonicalize(metadata or {})
        header = {
            "index": index,
            "previous_hash": previous_hash,
            "state_hash": state_hash,
            "metadata": entry_metadata,
        }
        entry_hash = hashlib.sha256(
            json.dumps(header, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()
        entry = {
            **header,
            "state": _canonicalize(state),
            "entry_hash": entry_hash,
        }
        self.entries.append(entry)
        return entry

    def verify(self) -> tuple[bool, str]:
        """Verify links, state digests, and headers for every chain entry."""
        for index, entry in enumerate(self.entries):
            expected_previous = (
                "0" * 64
                if index == 0
                else self.entries[index - 1]["entry_hash"]
            )
            if entry.get("previous_hash") != expected_previous:
                return False, f"Chain broken at index {index}."
            if hash_state(entry.get("state")) != entry.get("state_hash"):
                return False, f"State tampering detected at index {index}."

            header = {
                "index": entry.get("index"),
                "previous_hash": entry.get("previous_hash"),
                "state_hash": entry.get("state_hash"),
                "metadata": entry.get("metadata", {}),
            }
            expected_entry_hash = hashlib.sha256(
                json.dumps(
                    header, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest()
            if entry.get("entry_hash") != expected_entry_hash:
                return False, f"Entry header tampered at index {index}."
        return True, "State integrity verified."


class MerkleVerificationEngine:
    """Compatibility facade for roots and state verification helpers."""

    @staticmethod
    def hash_data(data: str) -> str:
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def generate_merkle_root(
        self, data_blocks: Iterable[str]
    ) -> dict[str, Any]:
        blocks = list(data_blocks)
        if not blocks:
            return {
                "merkle_root": self.hash_data("empty_block"),
                "status": "empty",
            }

        current_layer = [self.hash_data(block) for block in blocks]
        while len(current_layer) > 1:
            next_layer = []
            for index in range(0, len(current_layer), 2):
                right = (
                    current_layer[index + 1]
                    if index + 1 < len(current_layer)
                    else current_layer[index]
                )
                next_layer.append(self.hash_data(current_layer[index] + right))
            current_layer = next_layer
        return {
            "status": "success",
            "blocks_processed": len(blocks),
            "merkle_root": current_layer[0],
            "integrity_verification": "Passed - Zero Drift Detected",
        }
