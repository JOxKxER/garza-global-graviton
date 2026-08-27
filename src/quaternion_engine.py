"""Quaternion and 4D hypercube operations for vector datasets."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterable, Optional

import numpy as np


@dataclass(frozen=True)
class Quaternion:
    """A quaternion stored in scalar-first order: ``(w, x, y, z)``."""

    w: float
    x: float
    y: float
    z: float

    @classmethod
    def identity(cls) -> "Quaternion":
        return cls(1.0, 0.0, 0.0, 0.0)

    @classmethod
    def from_axis_angle(
        cls, axis: Iterable[float], angle: float
    ) -> "Quaternion":
        axis_array = np.asarray(tuple(axis), dtype=np.float64)
        if axis_array.shape != (3,):
            raise ValueError("axis must have exactly three components")
        axis_norm = np.linalg.norm(axis_array)
        if axis_norm == 0.0:
            raise ValueError("axis must be non-zero")
        half_angle = angle / 2.0
        vector = axis_array / axis_norm * np.sin(half_angle)
        return cls(
            float(np.cos(half_angle)),
            float(vector[0]),
            float(vector[1]),
            float(vector[2]),
        )

    def as_array(self) -> np.ndarray:
        return np.array([self.w, self.x, self.y, self.z], dtype=np.float64)

    def norm(self) -> float:
        return float(np.linalg.norm(self.as_array()))

    def normalized(self) -> "Quaternion":
        magnitude = self.norm()
        if magnitude == 0.0:
            raise ValueError("zero quaternion cannot be normalized")
        values = self.as_array() / magnitude
        return Quaternion(*map(float, values))

    def conjugate(self) -> "Quaternion":
        return Quaternion(self.w, -self.x, -self.y, -self.z)

    def multiply(self, other: "Quaternion") -> "Quaternion":
        return Quaternion(
            self.w * other.w
            - self.x * other.x
            - self.y * other.y
            - self.z * other.z,
            self.w * other.x
            + self.x * other.w
            + self.y * other.z
            - self.z * other.y,
            self.w * other.y
            - self.x * other.z
            + self.y * other.w
            + self.z * other.x,
            self.w * other.z
            + self.x * other.y
            - self.y * other.x
            + self.z * other.w,
        )

    def rotate_3d_dataset(
        self, vectors: Iterable[Iterable[float]]
    ) -> np.ndarray:
        """Rotate an ``(n, 3)`` dataset with ``q * v * q*``."""
        values = np.asarray(vectors, dtype=np.float64)
        if values.ndim != 2 or values.shape[1] != 3:
            raise ValueError("vectors must have shape (n, 3)")
        unit = self.normalized()
        q_vector = np.array([unit.x, unit.y, unit.z])
        cross_first = np.cross(q_vector, values)
        return values + 2.0 * np.cross(
            q_vector, cross_first + unit.w * values
        )


@dataclass(frozen=True)
class Quaternion4DRotation:
    """An SO(4) rotation represented by left and right unit quaternions."""

    left: Quaternion
    right: Quaternion

    def __post_init__(self) -> None:
        object.__setattr__(self, "left", self.left.normalized())
        object.__setattr__(self, "right", self.right.normalized())

    @classmethod
    def identity(cls) -> "Quaternion4DRotation":
        identity = Quaternion.identity()
        return cls(identity, identity)

    def matrix(self) -> np.ndarray:
        """Return the equivalent 4-by-4 matrix for ``(x, y, z, w)`` points."""
        basis = np.eye(4, dtype=np.float64)
        return self.apply(basis).T

    def apply(self, points: Iterable[Iterable[float]]) -> np.ndarray:
        """Apply ``left * p * right`` to an ``(n, 4)`` dataset."""
        values = np.asarray(points, dtype=np.float64)
        if values.ndim != 2 or values.shape[1] != 4:
            raise ValueError("points must have shape (n, 4)")

        output = np.empty_like(values)
        for index, (x, y, z, w) in enumerate(values):
            point = Quaternion(float(w), float(x), float(y), float(z))
            rotated = self.left.multiply(point).multiply(self.right)
            output[index] = (rotated.x, rotated.y, rotated.z, rotated.w)
        return output


def hypercube_vertices(
    half_extent: float = 1.0,
    center: Optional[Iterable[float]] = None,
) -> np.ndarray:
    """Generate the 16 vertices of a 4D hypercube."""
    if half_extent <= 0.0:
        raise ValueError("half_extent must be positive")
    center_array = np.zeros(4, dtype=np.float64)
    if center is not None:
        center_array = np.asarray(tuple(center), dtype=np.float64)
        if center_array.shape != (4,):
            raise ValueError("center must have exactly four components")
    vertices = np.asarray(
        list(product((-half_extent, half_extent), repeat=4)),
        dtype=np.float64,
    )
    return vertices + center_array
