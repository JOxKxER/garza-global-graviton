"""Zero-copy buffer pool over an anonymous mmap region.

Tactical use: bypasses per-allocation OS-level copies (the same principle
RDMA/DPDK use to skip kernel buffer copies) by handing every caller a
`memoryview` slice directly into one shared anonymous memory-mapped
region, instead of allocating and copying a fresh `bytes` object per
module buffer. A coalescing free-list allocator keeps the pool usable
under repeated allocate/free cycles typical of a streaming edge pipeline.
The free-list is guarded by a lock so concurrent worker threads can
allocate/free against the same pool without corrupting its bookkeeping.
"""

from __future__ import annotations

import mmap
import threading
from dataclasses import dataclass


@dataclass
class BufferHandle:
    """A zero-copy handle to one allocated region of the shared mmap pool."""

    offset: int
    size: int
    view: memoryview


class ZeroCopyBufferPool:
    """Anonymous mmap-backed pool with a coalescing free-list allocator."""

    def __init__(self, pool_size_bytes: int) -> None:
        """Allocate the backing anonymous mmap region of the given size."""
        if pool_size_bytes <= 0:
            raise ValueError("pool_size_bytes must be positive")
        self.pool_size_bytes = pool_size_bytes
        self._mmap = mmap.mmap(-1, pool_size_bytes)
        self._pool_view = memoryview(self._mmap)
        self._free_blocks: list[tuple[int, int]] = [(0, pool_size_bytes)]
        self._allocations: dict[int, int] = {}
        self._lock = threading.Lock()

    def allocate(self, size_bytes: int) -> BufferHandle:
        """Allocate a zero-copy buffer view from the free-list (first-fit).

        Tactical advantage: returns a `memoryview` slice directly into
        the shared mmap region -- no bytes are copied out to satisfy
        this call, matching true zero-copy semantics.
        """
        if size_bytes <= 0:
            raise ValueError("size_bytes must be positive")

        with self._lock:
            for index, (offset, block_size) in enumerate(self._free_blocks):
                if block_size < size_bytes:
                    continue

                del self._free_blocks[index]
                if block_size > size_bytes:
                    remainder_offset = offset + size_bytes
                    remainder_size = block_size - size_bytes
                    self._free_blocks.insert(
                        index, (remainder_offset, remainder_size)
                    )

                self._allocations[offset] = size_bytes
                view = self._pool_view[offset:offset + size_bytes]
                return BufferHandle(offset, size_bytes, view)

        raise MemoryError(f"no free block large enough for {size_bytes} bytes")

    def free(self, handle: BufferHandle) -> None:
        """Release a buffer back to the free-list, coalescing neighbors.

        Tactical advantage: adjacent free blocks are merged immediately,
        keeping the pool resistant to fragmentation under repeated
        allocate/free cycles.
        """
        if handle.offset not in self._allocations:
            raise ValueError("handle is not a live allocation in this pool")

        with self._lock:
            del self._allocations[handle.offset]
            handle.view.release()

            self._free_blocks.append((handle.offset, handle.size))
            self._free_blocks.sort(key=lambda block: block[0])
            self._coalesce()

    def _coalesce(self) -> None:
        """Merge adjacent free blocks into single larger free blocks."""
        merged: list[tuple[int, int]] = []
        for offset, size in self._free_blocks:
            if merged and merged[-1][0] + merged[-1][1] == offset:
                previous_offset, previous_size = merged.pop()
                merged.append((previous_offset, previous_size + size))
            else:
                merged.append((offset, size))
        self._free_blocks = merged

    def verify_zero_copy(self, handle: BufferHandle) -> bool:
        """Confirm a handle's view truly aliases the pool's backing buffer.

        Tactical advantage: an explicit runtime check -- via the buffer
        protocol's `.obj` attribute -- that no hidden copy was made,
        rather than trusting the zero-copy property by convention.
        """
        return handle.view.obj is self._mmap

    def get_free_blocks(self) -> list[tuple[int, int]]:
        """Return a snapshot of the current free-list (offset, size) pairs."""
        with self._lock:
            return list(self._free_blocks)

    def get_active_allocations(self) -> list[tuple[int, int]]:
        """Return a snapshot of current (offset, size) live allocations.

        Tactical advantage: gives an anti-tamper controller an exact
        accounting of how much live data existed at the moment an
        emergency purge was triggered, for after-action reporting.
        """
        with self._lock:
            return list(self._allocations.items())

    def wipe_entire_pool(self, pattern: bytes) -> None:
        """Overwrite every byte of the backing mmap region with pattern.

        `pattern` must be exactly `pool_size_bytes` long (zeros or
        cryptographic random noise are both valid fill sources).

        Tactical advantage: a single bulk memoryview assignment
        instantly destroys every live and free byte in the pool --
        active allocations included -- regardless of how many separate
        handles were outstanding, in one lock-protected operation.
        """
        if len(pattern) != self.pool_size_bytes:
            raise ValueError("pattern length must equal pool_size_bytes")
        with self._lock:
            self._pool_view[:] = pattern

    def close(self) -> None:
        """Release the pool view and close the underlying mmap region."""
        self._pool_view.release()
        self._mmap.close()


if __name__ == "__main__":
    pool = ZeroCopyBufferPool(pool_size_bytes=4096)

    handle_a = pool.allocate(256)
    handle_a.view[:5] = b"GGGGG"
    assert bytes(handle_a.view[:5]) == b"GGGGG"
    assert pool.verify_zero_copy(handle_a), "Allocation is not zero-copy."

    shared_view = handle_a.view[:5]
    shared_view[:1] = b"X"
    assert bytes(handle_a.view[:1]) == b"X", "Shared view mutation lost."
    shared_view.release()

    handle_b = pool.allocate(512)
    assert handle_b.offset == handle_a.offset + handle_a.size

    pool.free(handle_a)
    handle_c = pool.allocate(128)
    assert handle_c.offset == 0, "Free-list reuse failed to reclaim block."

    pool.free(handle_b)
    pool.free(handle_c)
    remaining_free_blocks = pool.get_free_blocks()
    assert remaining_free_blocks == [(0, 4096)], "Coalescing incomplete."

    pool.close()
    print("ZeroCopyBufferPool self-test passed.")
    print(f"Pool size: {pool.pool_size_bytes} bytes")
