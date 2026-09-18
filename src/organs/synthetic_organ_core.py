"""Garza Global Graviton (GGG) Synthetic Data Center Organ Core.

Models a data center's operational subsystems as biological organs, all
orchestrated by a single `SyntheticOrganCore`:

- pulse_heart:        microsecond-accurate cadence pacing.
- scrub_liver:        in-place vectorized memory zeroization of stale bytes.
- breathe_lungs:      zero-copy buffer inflate/deflate (inhale/exhale) flow.
- immune_system_scan: zero-trust anomaly detection with quarantine-zeroize.

All buffer state lives in one preallocated numpy array exposed only through
`memoryview` slices, so hot-path reads/writes never copy the backing store.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional, Tuple

import numpy as np


@dataclass
class OrganTelemetry:
    """Point-in-time health snapshot emitted by a single organ daemon.

    Attributes:
        organ_name: Which organ produced this sample (e.g. "heart").
        timestamp: Unix epoch seconds when the sample was captured.
        heart_rate_hz: Current pacing frequency of the Metabolic Heart, in Hz.
        waste_purged_bytes: Bytes zeroized by the Liver during this cycle.
        buffer_utilization: Ring buffer fill ratio in the range [0.0, 1.0].
        neutralized_threats: Count of anomalies quarantined this cycle.
        latency_ms: Wall-clock duration of the organ cycle, in milliseconds.
        healthy: Overall pass/fail health verdict for this sample.
    """

    organ_name: str
    timestamp: float
    heart_rate_hz: float
    waste_purged_bytes: int
    buffer_utilization: float
    neutralized_threats: int
    latency_ms: float
    healthy: bool

    def as_dict(self) -> dict:
        """Return a plain-dict representation suitable for JSON/logging."""
        return {
            "organ_name": self.organ_name,
            "timestamp": self.timestamp,
            "heart_rate_hz": round(self.heart_rate_hz, 4),
            "waste_purged_bytes": self.waste_purged_bytes,
            "buffer_utilization": round(self.buffer_utilization, 4),
            "neutralized_threats": self.neutralized_threats,
            "latency_ms": round(self.latency_ms, 4),
            "healthy": self.healthy,
        }


class ZeroCopyRingBuffer:
    """Fixed-capacity ring buffer backed by a single numpy array.

    All views handed out are `memoryview` slices over the same backing
    buffer, so no data is copied on read or write; only the read/write
    cursors move. This is the shared substrate used by the Lungs (inflate/
    deflate), Liver (scrub), and Immune System (zeroize) organs below.
    """

    def __init__(self, capacity_bytes: int) -> None:
        if capacity_bytes <= 0:
            raise ValueError("capacity_bytes must be a positive integer")
        self._capacity = capacity_bytes
        self._backing = np.zeros(capacity_bytes, dtype=np.uint8)
        self._view = memoryview(self._backing)
        self._write_cursor = 0
        self._read_cursor = 0
        self._filled = 0

    @property
    def capacity(self) -> int:
        """Total capacity of the ring buffer, in bytes."""
        return self._capacity

    @property
    def filled(self) -> int:
        """Number of bytes currently occupied in the ring."""
        return self._filled

    @property
    def free_space(self) -> int:
        """Number of bytes currently free in the ring."""
        return self._capacity - self._filled

    @property
    def backing_view(self) -> np.ndarray:
        """Read-only numpy view over the full backing array (zero-copy)."""
        return self._backing

    def write(self, payload: bytes) -> int:
        """Write ``payload`` into the ring without copying the backing array.

        Wraps around the ring boundary as needed. Returns the number of
        bytes actually written (truncated if the ring lacks free space).
        """
        writable = min(len(payload), self.free_space)
        if writable == 0:
            return 0

        source = np.frombuffer(payload[:writable], dtype=np.uint8)
        end_index = self._write_cursor + writable

        if end_index <= self._capacity:
            self._view[self._write_cursor:end_index] = source
        else:
            first_chunk = self._capacity - self._write_cursor
            self._view[self._write_cursor:self._capacity] = source[:first_chunk]
            self._view[0:end_index - self._capacity] = source[first_chunk:]

        self._write_cursor = end_index % self._capacity
        self._filled += writable
        return writable

    def read_view(self, length: int) -> memoryview:
        """Return a zero-copy ``memoryview`` over up to ``length`` unread bytes.

        Note: for data that wraps past the ring boundary, only the
        contiguous first segment is returned (bounded read), preserving the
        zero-copy guarantee. Advance with `advance_read` after consuming.
        """
        readable = min(length, self._filled, self._capacity - self._read_cursor)
        return self._view[self._read_cursor:self._read_cursor + readable]

    def advance_read(self, consumed: int) -> None:
        """Advance the read cursor after a caller consumes ``consumed`` bytes."""
        consumed = min(consumed, self._filled)
        self._read_cursor = (self._read_cursor + consumed) % self._capacity
        self._filled -= consumed

    def zeroize_all(self) -> int:
        """Vectorized zeroization of the entire backing array.

        Returns the number of bytes zeroized (equal to capacity).
        """
        self._backing[:] = 0
        self._read_cursor = 0
        self._write_cursor = 0
        self._filled = 0
        return self._capacity

    def zeroize_range(self, start: int, length: int) -> int:
        """Vectorized zeroization of a bounded, ring-aware byte range."""
        start = start % self._capacity
        length = min(length, self._capacity)
        end = start + length

        if end <= self._capacity:
            self._backing[start:end] = 0
        else:
            self._backing[start:self._capacity] = 0
            self._backing[0:end - self._capacity] = 0
        return length


class SyntheticOrganCore:
    """Orchestrates the Heart, Liver, Lungs, and Immune System daemons around
    one shared zero-copy ring buffer.

    Args:
        capacity_bytes: Size of the shared ring buffer, in bytes.
        target_hz: Target pacing frequency for `pulse_heart`, in Hz.
    """

    def __init__(
        self, capacity_bytes: int = 1 << 20, target_hz: float = 1000.0
    ) -> None:
        if target_hz <= 0:
            raise ValueError("target_hz must be positive")

        self.ring = ZeroCopyRingBuffer(capacity_bytes)
        self.target_hz = target_hz
        self._period_s = 1.0 / target_hz

        self._last_beat_ts = time.perf_counter()
        self._stale_ranges: Deque[Tuple[int, int]] = deque()
        self._signatures: List[np.ndarray] = []

    def register_threat_signature(self, signature: bytes) -> None:
        """Add a byte-pattern signature to the zero-trust anomaly scan set."""
        self._signatures.append(np.frombuffer(signature, dtype=np.uint8))

    def mark_waste(self, start: int, length: int) -> None:
        """Register a byte range as stale, eligible for the next scrub_liver call."""
        self._stale_ranges.append((start, length))

    def pulse_heart(self) -> OrganTelemetry:
        """Advance one heartbeat cycle with microsecond-accurate pacing.

        Busy-waits over the final ~200us of the period (after a coarse
        sleep) to tighten cadence precision beyond typical OS sleep jitter.
        """
        cycle_start = time.perf_counter()
        elapsed_since_last = cycle_start - self._last_beat_ts
        remaining = self._period_s - elapsed_since_last

        if remaining > 0:
            coarse_sleep = max(0.0, remaining - 200e-6)
            if coarse_sleep > 0:
                time.sleep(coarse_sleep)
            while time.perf_counter() - cycle_start < remaining:
                pass  # microsecond-precision spin for the final tail

        cycle_end = time.perf_counter()
        self._last_beat_ts = cycle_end

        actual_period = max(cycle_end - cycle_start, elapsed_since_last)
        heart_rate_hz = 1.0 / actual_period if actual_period > 0 else self.target_hz
        latency_ms = (cycle_end - cycle_start) * 1000.0

        return OrganTelemetry(
            organ_name="heart",
            timestamp=time.time(),
            heart_rate_hz=heart_rate_hz,
            waste_purged_bytes=0,
            buffer_utilization=self.ring.filled / self.ring.capacity,
            neutralized_threats=0,
            latency_ms=latency_ms,
            healthy=True,
        )

    def scrub_liver(self) -> OrganTelemetry:
        """Vectorized in-place zeroization of every registered stale byte
        range, then report telemetry for the cycle.
        """
        cycle_start = time.perf_counter()
        purged_this_cycle = 0

        while self._stale_ranges:
            start, length = self._stale_ranges.popleft()
            purged_this_cycle += self.ring.zeroize_range(start, length)

        latency_ms = (time.perf_counter() - cycle_start) * 1000.0

        return OrganTelemetry(
            organ_name="liver",
            timestamp=time.time(),
            heart_rate_hz=0.0,
            waste_purged_bytes=purged_this_cycle,
            buffer_utilization=self.ring.filled / self.ring.capacity,
            neutralized_threats=0,
            latency_ms=latency_ms,
            healthy=True,
        )

    def breathe_lungs(
        self, inhale_payload: Optional[bytes] = None, exhale_length: int = 0
    ) -> OrganTelemetry:
        """Run one inhale/exhale cycle to move data through the ring buffer.

        Args:
            inhale_payload: Optional bytes to write (zero-copy) into the ring.
            exhale_length: Unread bytes to release back to free space.
        """
        cycle_start = time.perf_counter()
        written = self.ring.write(inhale_payload) if inhale_payload else 0

        released = 0
        if exhale_length > 0:
            view = self.ring.read_view(exhale_length)
            released = len(view)
            self.ring.advance_read(released)

        latency_ms = (time.perf_counter() - cycle_start) * 1000.0
        expected_write = len(inhale_payload) if inhale_payload else 0

        return OrganTelemetry(
            organ_name="lungs",
            timestamp=time.time(),
            heart_rate_hz=0.0,
            waste_purged_bytes=0,
            buffer_utilization=self.ring.filled / self.ring.capacity,
            neutralized_threats=0,
            latency_ms=latency_ms,
            healthy=written == expected_write,
        )

    def _find_signature_matches(
        self, haystack: np.ndarray, needle: np.ndarray
    ) -> np.ndarray:
        """Vectorized substring search; returns start indices of all matches."""
        needle_len = len(needle)
        if needle_len == 0 or needle_len > len(haystack):
            return np.empty(0, dtype=np.int64)

        windows = np.lib.stride_tricks.sliding_window_view(haystack, needle_len)
        matches = np.all(windows == needle, axis=1)
        return np.flatnonzero(matches)

    def immune_system_scan(self) -> OrganTelemetry:
        """Zero-trust scan of the ring buffer for known threat signatures.

        Every match is treated as untrusted by default and immediately
        quarantined via in-place zeroization (never left readable) --
        quarantine equals neutralization under a zero-trust posture.
        """
        cycle_start = time.perf_counter()
        haystack = self.ring.backing_view
        neutralized = 0

        for signature in self._signatures:
            match_indices = self._find_signature_matches(haystack, signature)
            for start_index in match_indices:
                self.ring.zeroize_range(int(start_index), len(signature))
                neutralized += 1

        latency_ms = (time.perf_counter() - cycle_start) * 1000.0

        return OrganTelemetry(
            organ_name="immune_system",
            timestamp=time.time(),
            heart_rate_hz=0.0,
            waste_purged_bytes=0,
            buffer_utilization=self.ring.filled / self.ring.capacity,
            neutralized_threats=neutralized,
            latency_ms=latency_ms,
            healthy=neutralized == 0,
        )

    def run_cycle(self, inhale_payload: Optional[bytes] = None) -> List[OrganTelemetry]:
        """Run one full organ cycle: heartbeat, breathing, scrubbing, immunity."""
        return [
            self.pulse_heart(),
            self.breathe_lungs(inhale_payload=inhale_payload),
            self.scrub_liver(),
            self.immune_system_scan(),
        ]
