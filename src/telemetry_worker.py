"""Bounded asynchronous telemetry worker for 4D vector packets."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

try:
    from .spatial_pipeline import transform_4d_vectors
    from .dual_plane_runtime import DualPlaneRuntime
except ImportError:
    from spatial_pipeline import transform_4d_vectors
    from dual_plane_runtime import DualPlaneRuntime


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
        self.runtime = DualPlaneRuntime()
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
                vector = np.asarray(transformed, dtype=np.float64)
                mean_vector = vector.mean(axis=0)
                target = np.resize(mean_vector, 2)
                surface = np.resize(mean_vector, max(2, mean_vector.size))
                stream = self.runtime.stream_tensor(vector)
                trace = self.runtime.categorical_trace(
                    mean_vector, lambda value: value
                )
                fixpoint = self.runtime.least_fixpoint(
                    lambda value: 0.75 * value + 0.25 * target,
                    np.zeros_like(target),
                )
                route = self.runtime.gradient_descent_route(
                    source=(0.0, 0.0),
                    target=target,
                    congestion=(packet.points.shape[0] / 1000.0, 0.0),
                )
                soliton = self.runtime.encode_soliton(
                    mean_vector,
                    topology="hopfion" if packet.plane == "xw" else "toron",
                )
                coupled_state = self.runtime.converge(target, surface)
                packet.result = {
                    "packet_id": packet.packet_id,
                    "status": "success",
                    "point_count": int(transformed.shape[0]),
                    "sha256": hashlib.sha256(
                        transformed.tobytes()
                    ).hexdigest(),
                    "route": {
                        "steps": len(route.path),
                        "energy": route.energy,
                        "congestion_cost": route.congestion_cost,
                    },
                    "soliton": {
                        "topology": soliton.topology,
                        "winding_number": soliton.winding_number,
                        "payload_hash": soliton.payload_hash,
                        "amplitude": soliton.amplitude,
                    },
                    "coupled_state": {
                        "generation": coupled_state.generation,
                        "convergence_error": coupled_state.convergence_error,
                    },
                    "control_plane": {
                        "tensor_chunks": len(stream),
                        "trace_preserved": trace.preserved,
                        "fixpoint_converged": fixpoint.converged,
                        "fixpoint_iterations": fixpoint.iterations,
                        "fixpoint_residual": fixpoint.residual,
                    },
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
