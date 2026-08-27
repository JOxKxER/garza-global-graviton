"""Bounded asynchronous telemetry worker for 4D vector packets."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

try:
    from .spatial_pipeline import transform_4d_vectors
except ImportError:
    from spatial_pipeline import transform_4d_vectors


@dataclass
class TelemetryPacket:
    packet_id: str
    points: np.ndarray
    theta: float
    plane: str = "xw"
    result: Optional[dict[str, Any]] = None


class BackgroundTelemetryWorker:
    """Process queued telemetry in a controlled background task."""

    def __init__(self, max_queue_size: int = 256) -> None:
        if max_queue_size < 1:
            raise ValueError("max_queue_size must be positive")
        self.queue: asyncio.Queue[TelemetryPacket] = asyncio.Queue(
            maxsize=max_queue_size
        )
        self.processed_count = 0
        self.failed_count = 0
        self._task: Optional[asyncio.Task[None]] = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if not self.running:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        await self.queue.join()
        self._task.cancel()
        await asyncio.gather(self._task, return_exceptions=True)
        self._task = None

    async def submit(self, packet: TelemetryPacket) -> None:
        await self.queue.put(packet)

    async def _run(self) -> None:
        while True:
            packet = await self.queue.get()
            try:
                transformed = transform_4d_vectors(
                    packet.points, packet.theta, packet.plane
                )
                packet.result = {
                    "packet_id": packet.packet_id,
                    "status": "success",
                    "point_count": int(transformed.shape[0]),
                    "sha256": hashlib.sha256(
                        transformed.tobytes()
                    ).hexdigest(),
                }
                self.processed_count += 1
            except (TypeError, ValueError, OverflowError):
                self.failed_count += 1
                packet.result = {
                    "packet_id": packet.packet_id,
                    "status": "error",
                }
            finally:
                self.queue.task_done()
