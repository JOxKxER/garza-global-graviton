"""Local dual-plane runtime for vector routing and telemetry convergence.

The implementation is a bounded mathematical model for edge processing. It does
not issue hardware commands directly; callers receive validated packets and
routing metadata for a separate, explicitly authorized actuator boundary.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class ToroidalCoordinate:
    x: float
    y: float


@dataclass(frozen=True)
class LiquidRoute:
    source: ToroidalCoordinate
    target: ToroidalCoordinate
    path: tuple[ToroidalCoordinate, ...]
    energy: float
    congestion_cost: float


@dataclass(frozen=True)
class ExecutionSurface:
    """Quadratic execution surface projected from a market tensor."""

    torus: ToroidalCoordinate
    entry_score: float
    exit_score: float
    energy: float
    risk_budget: float


@dataclass(frozen=True)
class MeshFallback:
    """Selected analytical endpoint after quadratic failover routing."""

    endpoint: str
    route: LiquidRoute
    attempted: tuple[str, ...]


@dataclass(frozen=True)
class FixpointResult:
    """Bounded approximation of mu Phi = union Phi^n(bottom)."""

    value: np.ndarray
    iterations: int
    converged: bool
    residual: float


@dataclass(frozen=True)
class TraceResult:
    """Categorical trace over a local state transition."""

    input_hash: str
    output_hash: str
    preserved: bool
    metadata: dict[str, float | int | bool]


@dataclass(frozen=True)
class SolitonEnvelope:
    """Integrity envelope for a vector payload crossing noisy boundaries."""

    topology: str
    winding_number: int
    payload_hash: str
    amplitude: float


@dataclass
class CoupledPlaneState:
    """Slow spatial state coupled to a fast surface wavepacket."""

    background: np.ndarray
    surface: np.ndarray
    convergence_error: float = math.inf
    generation: int = 0


@dataclass
class DualPlaneRuntime:
    width: float = 16.0
    height: float = 16.0
    energy_a: float = 1.0
    energy_b: float = 0.1
    energy_c: float = 0.0
    step_size: float = 0.25
    state: CoupledPlaneState = field(
        default_factory=lambda: CoupledPlaneState(
            background=np.zeros(2, dtype=np.float64),
            surface=np.zeros(2, dtype=np.float64),
        )
    )

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("toroidal dimensions must be positive")
        if self.step_size <= 0:
            raise ValueError("step_size must be positive")

    def wrap(self, coordinate: Iterable[float]) -> ToroidalCoordinate:
        values = tuple(float(value) for value in coordinate)
        if len(values) != 2:
            raise ValueError("toroidal coordinates require two values")
        return ToroidalCoordinate(
            values[0] % self.width, values[1] % self.height
        )

    def quadratic_energy(self, load: float) -> float:
        """Evaluate V(h) = ah^2 + bh + c for a local routing load."""
        return self.energy_a * load**2 + self.energy_b * load + self.energy_c

    def project_market_tensor(
        self,
        features: Iterable[float],
        risk_budget: float,
    ) -> ExecutionSurface:
        """Map market tensors to a torus and slide to a quadratic optimum."""
        values = np.asarray(tuple(features), dtype=np.float64)
        if values.size < 2 or not np.isfinite(values).all():
            raise ValueError("market tensor needs two finite dimensions")
        scale = np.linalg.norm(values)
        normalized = values / scale if scale else values
        torus = self.wrap(
            (normalized[0] * self.width, normalized[1] * self.height)
        )
        momentum = float(normalized[0])
        friction = abs(float(normalized[1]))
        curvature = 1.0 + float(np.var(values))
        linear = friction - momentum
        optimum = -linear / (2.0 * curvature)
        entry_score = min(1.0, max(0.0, 0.5 + optimum))
        exit_score = min(1.0, max(0.0, 0.5 - optimum))
        return ExecutionSurface(
            torus=torus,
            entry_score=entry_score,
            exit_score=exit_score,
            energy=self.quadratic_energy(curvature * optimum),
            risk_budget=max(0.0, risk_budget),
        )

    def route_with_failover(
        self,
        source: Iterable[float],
        target: Iterable[float],
        endpoints: Iterable[str],
        congestion: Iterable[float] = (),
        endpoint_health: dict[str, bool] | None = None,
    ) -> MeshFallback:
        """Select the lowest-energy analytical endpoint from a mesh."""
        health = endpoint_health or {}
        candidates = tuple(
            endpoint for endpoint in endpoints if health.get(endpoint, True)
        )
        if not candidates:
            raise RuntimeError("no healthy mesh endpoints are available")
        routes = [
            (self.gradient_descent_route(source, target, congestion), endpoint)
            for endpoint in candidates
        ]
        route, endpoint = min(routes, key=lambda item: item[0].energy)
        return MeshFallback(endpoint, route, candidates)

    def stream_tensor(
        self,
        tensor: np.ndarray,
        chunk_size: int = 1024,
    ) -> tuple[dict[str, float | int], ...]:
        """Process high-rate vectors in bounded surface-plane chunks."""
        values = np.asarray(tensor, dtype=np.float64)
        if values.ndim == 0 or not np.isfinite(values).all():
            raise ValueError("tensor must contain finite numeric values")
        if chunk_size < 1:
            raise ValueError("chunk_size must be positive")
        flat = values.reshape(-1)
        chunks = []
        for start in range(0, flat.size, chunk_size):
            chunk = flat[start:start + chunk_size]
            chunks.append(
                {
                    "offset": start,
                    "size": int(chunk.size),
                    "norm": float(np.linalg.norm(chunk)),
                    "mean": float(chunk.mean()) if chunk.size else 0.0,
                }
            )
        return tuple(chunks)

    def categorical_trace(
        self,
        value: np.ndarray,
        transition,
    ) -> TraceResult:
        """Apply a local transition and verify its traced state hashes."""
        input_value = np.asarray(value, dtype=np.float64)
        output_value = np.asarray(
            transition(input_value.copy()), dtype=np.float64
        )
        input_hash = hashlib.sha256(input_value.tobytes()).hexdigest()
        output_hash = hashlib.sha256(output_value.tobytes()).hexdigest()
        return TraceResult(
            input_hash=input_hash,
            output_hash=output_hash,
            preserved=input_value.shape == output_value.shape,
            metadata={
                "input_norm": float(np.linalg.norm(input_value)),
                "output_norm": float(np.linalg.norm(output_value)),
            },
        )

    def least_fixpoint(
        self,
        update,
        bottom: np.ndarray,
        max_iterations: int = 64,
        tolerance: float = 1e-6,
    ) -> FixpointResult:
        """Iterate a monotone-style local update from bottom to convergence."""
        value = np.asarray(bottom, dtype=np.float64)
        if max_iterations < 1 or tolerance <= 0:
            raise ValueError("invalid fixpoint convergence parameters")
        for iteration in range(1, max_iterations + 1):
            next_value = np.asarray(update(value.copy()), dtype=np.float64)
            if next_value.shape != value.shape:
                raise ValueError("fixpoint update changed tensor shape")
            residual = float(np.linalg.norm(next_value - value))
            value = next_value
            if residual <= tolerance:
                return FixpointResult(value, iteration, True, residual)
        return FixpointResult(value, max_iterations, False, residual)

    def gradient_descent_route(
        self,
        source: Iterable[float],
        target: Iterable[float],
        congestion: Iterable[float] = (),
        max_steps: int = 128,
    ) -> LiquidRoute:
        """Follow the lowest-energy wrapped direction toward a target."""
        current = self.wrap(source)
        destination = self.wrap(target)
        congestion_values = tuple(float(value) for value in congestion)
        path = [current]
        total_energy = 0.0

        for _ in range(max_steps):
            dx = _wrapped_delta(current.x, destination.x, self.width)
            dy = _wrapped_delta(current.y, destination.y, self.height)
            if math.hypot(dx, dy) < 1e-9:
                break
            candidates = []
            for axis, delta in enumerate((dx, dy)):
                if abs(delta) < 1e-9:
                    continue
                direction = 1.0 if delta > 0 else -1.0
                values = [current.x, current.y]
                values[axis] += direction
                next_point = self.wrap(values)
                local_load = (
                    congestion_values[axis]
                    if axis < len(congestion_values)
                    else 0.0
                )
                cost = self.quadratic_energy(abs(delta) + local_load)
                candidates.append((cost, next_point))
            _, current = min(candidates, key=lambda item: item[0])
            total_energy += min(candidates, key=lambda item: item[0])[0]
            path.append(current)

        return LiquidRoute(
            source=self.wrap(source),
            target=destination,
            path=tuple(path),
            energy=total_energy,
            congestion_cost=self.quadratic_energy(sum(congestion_values)),
        )

    def encode_soliton(
        self,
        vector: Iterable[float],
        topology: str = "hopfion",
        winding_number: int = 1,
    ) -> SolitonEnvelope:
        values = np.asarray(tuple(vector), dtype=np.float64)
        if values.size == 0:
            raise ValueError("soliton payload cannot be empty")
        if topology not in {"hopfion", "toron"}:
            raise ValueError("topology must be hopfion or toron")
        if winding_number == 0:
            raise ValueError("winding_number cannot be zero")
        return SolitonEnvelope(
            topology=topology,
            winding_number=winding_number,
            payload_hash=hashlib.sha256(values.tobytes()).hexdigest(),
            amplitude=float(np.linalg.norm(values)),
        )

    def converge(
        self,
        background_target: Iterable[float],
        surface_wavepacket: Iterable[float],
        max_iterations: int = 32,
        tolerance: float = 1e-6,
    ) -> CoupledPlaneState:
        """Apply mu Phi = union Phi^n(bottom) until the planes converge."""
        target = np.asarray(tuple(background_target), dtype=np.float64)
        surface = np.asarray(tuple(surface_wavepacket), dtype=np.float64)
        if target.shape != self.state.background.shape:
            raise ValueError(
                "background target must match the spatial state shape"
            )
        if surface.size == 0:
            raise ValueError("surface wavepacket cannot be empty")

        for generation in range(1, max_iterations + 1):
            coupled_target = 0.8 * target + 0.2 * surface[: target.size]
            next_background = self.state.background + self.step_size * (
                coupled_target - self.state.background
            )
            next_surface = 0.8 * surface + 0.2 * np.resize(
                next_background, surface.shape
            )
            error = float(
                np.linalg.norm(next_background - self.state.background)
            )
            self.state = CoupledPlaneState(
                background=next_background,
                surface=next_surface,
                convergence_error=error,
                generation=generation,
            )
            if error <= tolerance:
                break
        return self.state


def _wrapped_delta(source: float, target: float, size: float) -> float:
    direct = target - source
    return (direct + size / 2) % size - size / 2
