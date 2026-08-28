"""Builds the tamper-evident AuditManifest for one execution run.

The monitor interfaces below are intentionally narrow: real deployments feed
`NetworkActivityMonitor` from platform-native zero-network evidence sources
(Linux: auditd rules on socket()/connect()/sendto()/bind(), or an eBPF
tracer; Windows: ETW `Microsoft-Windows-Kernel-Network`; a hypervisor-level
tap is preferred over in-guest monitoring alone, since it cannot be disabled
by anything running inside the guest). `LocalReferenceMonitor` is a portable
fallback using only the standard library + psutil-style interface counters,
suitable for demos and CI, and clearly weaker than a hypervisor/eBPF tap.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Protocol

from .merkle import MerkleTree
from .schemas import AuditManifest, EventType, ExecutionEvent, _utc_now_iso


class NetworkActivityMonitor(Protocol):
    """Returns a snapshot dict of network-relevant counters. Every key here
    is checked by the verifier's zero-network invariant, so add new evidence
    sources as new keys rather than nesting/renaming existing ones."""

    def snapshot(self) -> Dict[str, Any]:
        ...


@dataclass
class LocalReferenceMonitor:
    """Portable, software-only monitor: counts active network interfaces
    (excluding loopback) and open sockets belonging to the job's process
    tree. This is a corroborating signal, not a substitute for a
    hypervisor/eBPF-level tap in a production deployment."""

    def snapshot(self) -> Dict[str, Any]:
        import socket

        try:
            import psutil  # optional dependency; degrade gracefully if absent

            interfaces = psutil.net_if_stats()
            up_non_loopback = [
                name
                for name, stats in interfaces.items()
                if stats.isup and name.lower() not in ("lo", "loopback")
            ]
            connections = psutil.net_connections(kind="inet")
            active_sockets = [c for c in connections if c.status != "NONE"]
            return {
                "interfaces_up_non_loopback": up_non_loopback,
                "interfaces_up_non_loopback_count": len(up_non_loopback),
                "active_inet_sockets_count": len(active_sockets),
                "hostname": socket.gethostname(),
            }
        except ImportError:
            return {
                "interfaces_up_non_loopback": None,
                "interfaces_up_non_loopback_count": None,
                "active_inet_sockets_count": None,
                "note": "psutil not installed; install it for interface/socket evidence",
            }


class AuditManifestBuilder:
    """Accumulates ExecutionEvents for one job and seals them into an
    AuditManifest bound by a single Merkle root."""

    def __init__(self, commitment_id: str, network_monitor: NetworkActivityMonitor):
        self.commitment_id = commitment_id
        self._network_monitor = network_monitor
        self._events: List[ExecutionEvent] = []
        self._seq = 0

    def _append(self, event_type: EventType, payload: Dict[str, Any]) -> None:
        self._events.append(
            ExecutionEvent(
                seq=self._seq,
                event_type=event_type,
                timestamp=_utc_now_iso(),
                payload=payload,
            )
        )
        self._seq += 1

    def record_process_start(self, job_label: str) -> None:
        self._append(EventType.PROCESS_START, {"job_label": job_label})
        self.record_network_snapshot()

    def record_network_snapshot(self) -> None:
        self._append(EventType.NET_IFACE_SNAPSHOT, self._network_monitor.snapshot())

    def record_syscall_category_counts(self, counts: Dict[str, int]) -> None:
        """`counts` should be a small, non-proprietary summary such as
        {"file_io": 4213, "socket": 0, "connect": 0, "sendto": 0, "bind": 0,
        "process_exec": 12} -- never raw syscall arguments or file paths."""
        self._append(EventType.SYSCALL_SNAPSHOT, {"counts": counts})

    def record_anomaly(self, description: str, evidence: Dict[str, Any]) -> None:
        self._append(EventType.ANOMALY, {"description": description, "evidence": evidence})

    def record_process_end(self, exit_code: int) -> None:
        self.record_network_snapshot()
        self._append(EventType.PROCESS_END, {"exit_code": exit_code})

    def seal(self) -> AuditManifest:
        if not self._events:
            raise ValueError("cannot seal a manifest with zero events")
        leaves = [event.canonical_bytes() for event in self._events]
        tree = MerkleTree(leaves)
        return AuditManifest(
            manifest_id=str(uuid.uuid4()),
            commitment_id=self.commitment_id,
            events=list(self._events),
            merkle_root=tree.root.hex(),
            leaf_count=tree.leaf_count,
            sealed_at=_utc_now_iso(),
        )
