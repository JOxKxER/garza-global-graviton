"""Domain-separated Merkle tree + G-code execution manifest.

This module is self-contained (stdlib only) so it can be handed to a client
verifier without pulling in unrelated packages -- see verify_cnc_client.py.

Merkle construction notes (identical rationale to any correct implementation
of RFC 6962-style trees, restated here since this module must stand alone):

* Leaf and internal nodes are hashed with distinct one-byte domain prefixes
  (0x00 for leaves, 0x01 for internal nodes). Without this separation an
  attacker can present an internal node as if it were a leaf (or vice versa)
  and forge a valid-looking proof for a G-code line that was never executed.
* An odd trailing node is promoted unchanged to the next level instead of
  being duplicated against itself -- duplicating the last node would let two
  different execution logs (one with N events, one with N+1 duplicating the
  last) produce the same root, breaking the "one root <-> one exact log"
  property the whole protocol depends on.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Sequence, Tuple

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
    sibling_is_right: bool


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
                    MerkleProofStep(sibling=level[sibling_idx], sibling_is_right=not is_right_node)
                )
            idx //= 2
        return steps

    @staticmethod
    def verify_proof(leaf_data: bytes, proof: Sequence[MerkleProofStep], expected_root: bytes) -> bool:
        current = leaf_hash(leaf_data)
        for step in proof:
            current = (
                node_hash(current, step.sibling)
                if step.sibling_is_right
                else node_hash(step.sibling, current)
            )
        return current == expected_root


def encode_proof(proof: Sequence[MerkleProofStep]) -> List[Tuple[str, str]]:
    return [(step.sibling.hex(), "R" if step.sibling_is_right else "L") for step in proof]


def decode_proof(encoded: Sequence[Tuple[str, str]]) -> List[MerkleProofStep]:
    return [MerkleProofStep(bytes.fromhex(h), side == "R") for h, side in encoded]


# --------------------------------------------------------------------------
# Commit-reveal blinding for the client's submitted G-code sample
# --------------------------------------------------------------------------

def compute_gcode_commitment(gcode_bytes: bytes, salt: bytes) -> str:
    """Client-side: hex sha256(gcode || salt). Send only this hash (plus an
    encrypted copy of the file) to the vendor's intake; keep `salt` secret
    until the reveal step after the job is attested."""
    return hashlib.sha256(gcode_bytes + salt).hexdigest()


def verify_gcode_reveal(gcode_bytes: bytes, salt: bytes, commitment_hash: str) -> bool:
    """Client-side reveal check: confirms the vendor actually ran the exact
    bytes committed to in step 1, not a substituted file."""
    return compute_gcode_commitment(gcode_bytes, salt) == commitment_hash


# --------------------------------------------------------------------------
# Execution manifest: what the isolated controller records while running
# --------------------------------------------------------------------------

class GCodeEventType(str, Enum):
    JOB_START = "JOB_START"
    LINE_EXECUTED = "LINE_EXECUTED"
    TOOL_CHANGE = "TOOL_CHANGE"
    SPINDLE_STATE = "SPINDLE_STATE"
    JOB_END = "JOB_END"
    ANOMALY = "ANOMALY"


def _utc_now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass
class GCodeExecutionEvent:
    seq: int
    event_type: GCodeEventType
    timestamp: str
    payload: Dict[str, Any]

    def canonical_bytes(self) -> bytes:
        return _canonical_json(
            {
                "seq": self.seq,
                "event_type": self.event_type.value,
                "timestamp": self.timestamp,
                "payload": self.payload,
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seq": self.seq,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "GCodeExecutionEvent":
        return GCodeExecutionEvent(
            seq=data["seq"],
            event_type=GCodeEventType(data["event_type"]),
            timestamp=data["timestamp"],
            payload=data["payload"],
        )


@dataclass
class GCodeAuditManifest:
    manifest_id: str
    commitment_id: str
    events: List[GCodeExecutionEvent]
    merkle_root: str
    leaf_count: int
    sealed_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "commitment_id": self.commitment_id,
            "events": [e.to_dict() for e in self.events],
            "merkle_root": self.merkle_root,
            "leaf_count": self.leaf_count,
            "sealed_at": self.sealed_at,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "GCodeAuditManifest":
        return GCodeAuditManifest(
            manifest_id=data["manifest_id"],
            commitment_id=data["commitment_id"],
            events=[GCodeExecutionEvent.from_dict(e) for e in data["events"]],
            merkle_root=data["merkle_root"],
            leaf_count=data["leaf_count"],
            sealed_at=data["sealed_at"],
        )


def recompute_merkle_root(manifest: GCodeAuditManifest) -> bytes:
    leaves = [event.canonical_bytes() for event in manifest.events]
    return MerkleTree(leaves).root


class GCodeManifestBuilder:
    """Runs on the isolated CNC controller (or its attached single-board
    companion) while a job executes. Line content is never stored verbatim
    in the manifest -- only a per-job-salted hash of each line -- so the
    sealed log can be handed to the client without re-exposing the full
    toolpath in transit; the client already has the plaintext and can
    recompute the same per-line hashes locally to spot-check any line.
    """

    def __init__(self, commitment_id: str, job_salt: bytes):
        self.commitment_id = commitment_id
        self._job_salt = job_salt
        self._events: List[GCodeExecutionEvent] = []
        self._seq = 0

    def _append(self, event_type: GCodeEventType, payload: Dict[str, Any]) -> None:
        self._events.append(
            GCodeExecutionEvent(
                seq=self._seq, event_type=event_type, timestamp=_utc_now_iso(), payload=payload
            )
        )
        self._seq += 1

    def line_hash(self, gcode_line: str) -> str:
        return hashlib.sha256(self._job_salt + gcode_line.encode("utf-8")).hexdigest()

    def record_job_start(self, job_label: str, total_lines: int) -> None:
        self._append(GCodeEventType.JOB_START, {"job_label": job_label, "total_lines": total_lines})

    def record_line_executed(self, line_number: int, gcode_line: str) -> None:
        self._append(
            GCodeEventType.LINE_EXECUTED,
            {"line_number": line_number, "line_hash": self.line_hash(gcode_line)},
        )

    def record_tool_change(self, tool_id: str) -> None:
        self._append(GCodeEventType.TOOL_CHANGE, {"tool_id": tool_id})

    def record_spindle_state(self, rpm: float, enabled: bool) -> None:
        self._append(GCodeEventType.SPINDLE_STATE, {"rpm": rpm, "enabled": enabled})

    def record_anomaly(self, description: str, evidence: Dict[str, Any]) -> None:
        self._append(GCodeEventType.ANOMALY, {"description": description, "evidence": evidence})

    def record_job_end(self, lines_executed: int, completed: bool) -> None:
        self._append(GCodeEventType.JOB_END, {"lines_executed": lines_executed, "completed": completed})

    def seal(self) -> GCodeAuditManifest:
        if not self._events:
            raise ValueError("cannot seal a manifest with zero events")
        leaves = [event.canonical_bytes() for event in self._events]
        tree = MerkleTree(leaves)
        return GCodeAuditManifest(
            manifest_id=str(uuid.uuid4()),
            commitment_id=self.commitment_id,
            events=list(self._events),
            merkle_root=tree.root.hex(),
            leaf_count=tree.leaf_count,
        )
