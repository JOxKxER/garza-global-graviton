"""Asynchronous ingestion and initial 4D spatial transformation pipeline."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Iterable, Optional

import numpy as np

try:
    from .core import transform_4d_dataset
except ImportError:
    from core import transform_4d_dataset


@dataclass(frozen=True)
class SpatialVectorPacket:
    """A finite batch of points and the rotation parameters to apply."""

    packet_id: str
    points: np.ndarray
    theta: float
    plane: str = "xw"
    double_theta: Optional[float] = None


def transform_4d_vectors(
    points: Iterable[Iterable[float]],
    theta: float,
    plane: str = "xw",
    double_theta: Optional[float] = None,
) -> np.ndarray:
    """Validate and transform a collection of four-dimensional points."""
    point_array = np.asarray(points, dtype=np.float64)
    if point_array.ndim != 2 or point_array.shape[1] != 4:
        raise ValueError("points must have shape (n, 4)")
    return transform_4d_dataset(point_array, theta, plane, double_theta)


class AsyncSpatialVectorPipeline:
    """Queue and transform finite batches with bounded concurrency."""

    def __init__(self, max_queue_size: int = 256) -> None:
        if max_queue_size < 1:
            raise ValueError("max_queue_size must be positive")
        self.queue: asyncio.Queue[SpatialVectorPacket] = asyncio.Queue(
            maxsize=max_queue_size
        )
        self.processed_count = 0

    async def ingest(self, packet: SpatialVectorPacket) -> dict[str, str]:
        """Enqueue a packet, applying backpressure when the queue is full."""
        await self.queue.put(packet)
        return {"status": "queued", "packet_id": packet.packet_id}

    async def _worker(self, results: list[dict[str, Any]]) -> None:
        while True:
            packet = await self.queue.get()
            try:
                transformed = transform_4d_vectors(
                    packet.points,
                    packet.theta,
                    packet.plane,
                    packet.double_theta,
                )
                results.append(
                    {
                        "packet_id": packet.packet_id,
                        "status": "transformed",
                        "points": transformed,
                    }
                )
                self.processed_count += 1
            finally:
                self.queue.task_done()

    async def process_pending(
        self, worker_count: int = 1
    ) -> list[dict[str, Any]]:
        """Process queued packets and return completion results."""
        if worker_count < 1:
            raise ValueError("worker_count must be positive")

        results: list[dict[str, Any]] = []
        workers = [
            asyncio.create_task(self._worker(results))
            for _ in range(worker_count)
        ]
        try:
            await self.queue.join()
        finally:
            for worker in workers:
                worker.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
        return results
