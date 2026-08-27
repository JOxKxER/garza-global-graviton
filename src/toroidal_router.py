"""Shortest-path routing on a bounded two-dimensional toroidal mesh."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ToroidalRoute:
    source: tuple[int, int]
    target: tuple[int, int]
    distance: float
    estimated_latency_ms: float


class ToroidalMeshRouter:
    """Calculate wraparound distance and deterministic route metrics."""

    def __init__(self, width: int = 16, height: int = 16) -> None:
        if width < 1 or height < 1:
            raise ValueError("mesh dimensions must be positive")
        self.width = width
        self.height = height

    def _node(self, node: Iterable[int]) -> tuple[int, int]:
        values = tuple(node)
        if len(values) != 2:
            raise ValueError("mesh nodes must have two coordinates")
        return values[0] % self.width, values[1] % self.height

    def distance(self, source: Iterable[int], target: Iterable[int]) -> float:
        source_node = self._node(source)
        target_node = self._node(target)
        dx = min(
            abs(source_node[0] - target_node[0]),
            self.width - abs(source_node[0] - target_node[0]),
        )
        dy = min(
            abs(source_node[1] - target_node[1]),
            self.height - abs(source_node[1] - target_node[1]),
        )
        return math.hypot(dx, dy)

    def route(
        self,
        source: Iterable[int],
        target: Iterable[int],
        payload_size_kb: float = 0.0,
    ) -> ToroidalRoute:
        if payload_size_kb < 0.0:
            raise ValueError("payload_size_kb cannot be negative")
        source_node = self._node(source)
        target_node = self._node(target)
        distance = self.distance(source_node, target_node)
        latency = distance * 1.42 + payload_size_kb * 0.001
        return ToroidalRoute(
            source_node,
            target_node,
            distance,
            round(latency, 3),
        )
