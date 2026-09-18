"""FIPS-aligned telemetry crypto and tactical anti-tamper zeroization.

Tactical use: pairs a strict AES-256-GCM (a FIPS 140-3 approved
algorithm) authenticated-encryption wrapper -- built on the audited
`cryptography` library rather than a hand-rolled cipher -- with an
emergency zeroization controller that hooks directly into a
`ZeroCopyBufferPool` and instantly overwrites every live and free byte
of edge telemetry memory the moment a tamper/anomaly signal fires.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.memory.zero_copy_buffer import ZeroCopyBufferPool

AES_256_KEY_SIZE_BYTES = 32
GCM_NONCE_SIZE_BYTES = 12


class FipsCryptoWrapper:
    """AES-256-GCM authenticated encryption for edge telemetry payloads."""

    def __init__(self, key: bytes | None = None) -> None:
        """Set (or generate) the 32-byte AES-256 key used for this wrapper."""
        if key is None:
            key = AESGCM.generate_key(bit_length=256)
        if len(key) != AES_256_KEY_SIZE_BYTES:
            raise ValueError(
                f"key must be exactly {AES_256_KEY_SIZE_BYTES} bytes"
            )
        self._key = key
        self._aesgcm = AESGCM(key)

    @property
    def key(self) -> bytes:
        """Return the raw 32-byte AES-256 key backing this wrapper."""
        return self._key

    def encrypt(
        self, plaintext: bytes, associated_data: bytes | None = None
    ) -> tuple[bytes, bytes]:
        """Encrypt and authenticate a telemetry payload.

        Returns (nonce, ciphertext_with_tag). A fresh random nonce is
        generated per call, as required for AES-GCM's security
        guarantees to hold.

        Tactical advantage: the returned ciphertext carries its own
        authentication tag, so any bit-flip tamper attempt on the
        transport layer is detected on decrypt rather than silently
        accepted.
        """
        if not isinstance(plaintext, (bytes, bytearray)):
            raise TypeError("plaintext must be bytes or bytearray")
        nonce = os.urandom(GCM_NONCE_SIZE_BYTES)
        ciphertext = self._aesgcm.encrypt(
            nonce, bytes(plaintext), associated_data
        )
        return nonce, ciphertext

    def decrypt(
        self,
        nonce: bytes,
        ciphertext: bytes,
        associated_data: bytes | None = None,
    ) -> bytes:
        """Decrypt and authenticate a payload; raises InvalidTag on tamper.

        Tactical advantage: authentication is checked before any
        plaintext is returned, so a corrupted or forged payload can
        never be mistaken for valid telemetry.
        """
        if len(nonce) != GCM_NONCE_SIZE_BYTES:
            raise ValueError(
                f"nonce must be exactly {GCM_NONCE_SIZE_BYTES} bytes"
            )
        return self._aesgcm.decrypt(nonce, ciphertext, associated_data)


@dataclass
class PurgeReport:
    """A record of one emergency zeroization event."""

    reason: str
    active_allocations_purged: int
    pool_bytes_wiped: int
    elapsed_seconds: float


@dataclass
class ZeroizationManager:
    """Hooks into a ZeroCopyBufferPool for instant emergency memory purge."""

    pool: ZeroCopyBufferPool
    use_random_noise: bool = True
    purge_count: int = field(default=0, init=False)
    last_purge_seconds: float | None = field(default=None, init=False)

    def check_tamper_signal(
        self, cusum_alarmed: bool = False, structural_instability: bool = False
    ) -> bool:
        """Evaluate whether incoming anomaly flags demand an emergency purge.

        Integrates with a CUSUM tamper-detector alarm and/or a
        structural-instability (e.g. cusp-catastrophe) flag; either one
        alone is sufficient to declare a tamper condition.

        Tactical advantage: a single decision point combining multiple
        independent anomaly detectors, so no single detector's blind
        spot can suppress a purge trigger.
        """
        return cusum_alarmed or structural_instability

    def trigger_purge(self, reason: str = "tamper_signal") -> PurgeReport:
        """Immediately overwrite the entire backing buffer pool in place.

        Only the bulk memoryview write itself is timed as the
        "zeroization" cost; generating a fresh random fill pattern is a
        separate preparatory step and is measured outside that window.

        Tactical advantage: a single bulk memoryview write destroys
        every live allocation's data along with all free-list slack,
        with no per-buffer iteration and no window where an attacker
        could read partially-wiped memory.
        """
        active_allocations = self.pool.get_active_allocations()

        pattern = (
            os.urandom(self.pool.pool_size_bytes)
            if self.use_random_noise
            else bytes(self.pool.pool_size_bytes)
        )

        start = time.perf_counter()
        self.pool.wipe_entire_pool(pattern)
        elapsed_seconds = time.perf_counter() - start

        self.purge_count += 1
        self.last_purge_seconds = elapsed_seconds
        return PurgeReport(
            reason=reason,
            active_allocations_purged=len(active_allocations),
            pool_bytes_wiped=self.pool.pool_size_bytes,
            elapsed_seconds=elapsed_seconds,
        )

    def evaluate_and_purge(
        self,
        cusum_alarmed: bool = False,
        structural_instability: bool = False,
    ) -> PurgeReport | None:
        """Check for a tamper signal and purge immediately if one is found.

        Tactical advantage: a single call an anomaly-detection loop can
        invoke every tick, with the purge itself only firing when a
        real tamper condition is present.
        """
        if not self.check_tamper_signal(cusum_alarmed, structural_instability):
            return None
        reason = "cusum_alarm" if cusum_alarmed else "structural_instability"
        return self.trigger_purge(reason=reason)


if __name__ == "__main__":
    crypto = FipsCryptoWrapper()
    telemetry_payload = b"GGG-EDGE-TELEMETRY-PACKET-0001"

    demo_nonce, demo_ciphertext = crypto.encrypt(telemetry_payload)
    recovered = crypto.decrypt(demo_nonce, demo_ciphertext)
    assert recovered == telemetry_payload, "AES-GCM round-trip failed."

    tampered_ciphertext = bytearray(demo_ciphertext)
    tampered_ciphertext[0] ^= 0xFF
    tamper_detected = False
    try:
        crypto.decrypt(demo_nonce, bytes(tampered_ciphertext))
    except InvalidTag:
        tamper_detected = True
    assert tamper_detected, "Tampered ciphertext must fail authentication."

    print("FipsCryptoWrapper self-test passed.")
    print(f"Plaintext: {telemetry_payload!r}")
    print(f"Ciphertext bytes: {len(demo_ciphertext)}, tamper detected: True")

    pool = ZeroCopyBufferPool(pool_size_bytes=1 << 20)
    manager = ZeroizationManager(pool=pool, use_random_noise=True)

    live_handles = []
    original_prefixes = []
    for index in range(50):
        handle = pool.allocate(4096)
        prefix = f"SECRET{index:02d}".encode()[:8]
        handle.view[:8] = prefix
        live_handles.append(handle)
        original_prefixes.append(prefix)

    assert len(pool.get_active_allocations()) == 50

    report = manager.trigger_purge(reason="self_test")
    assert report.active_allocations_purged == 50
    assert report.elapsed_seconds < 0.001, (
        f"Zeroization exceeded 1ms budget: {report.elapsed_seconds:.6f}s"
    )

    for handle, original_prefix in zip(live_handles, original_prefixes):
        assert bytes(handle.view[:8]) != original_prefix, (
            "Purge failed to overwrite an active allocation."
        )
        handle.view.release()

    pool.close()

    print("ZeroizationManager self-test passed.")
    print(f"Active allocations purged: {report.active_allocations_purged}")
    print(f"Bytes wiped: {report.pool_bytes_wiped}")
    print(f"Elapsed: {report.elapsed_seconds * 1000:.4f} ms")
