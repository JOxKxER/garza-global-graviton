"""
Garza Global Graviton (GGG) Project - Engine Core
Synthesizes: Quaternionic Spatial Transformations, Heighway Dragon Fractal Indexing,
Kinematic Trochoidal Trajectories, and Pure Math Field Scaling.
Zero external dependencies (uses standard library math/cmath only).
"""

import math
import cmath


class Quaternion:
    """4D Hypercomplex Number System using standard math operations."""

    def __init__(self, w: float, x: float, y: float, z: float):
        self.w = float(w)
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    @classmethod
    def from_axis_angle(cls, axis: list[float], angle: float):
        norm = math.sqrt(sum(a * a for a in axis)) + 1e-12
        normalized_axis = [a / norm for a in axis]
        half_angle = angle / 2.0
        sin_half = math.sin(half_angle)
        return cls(
            math.cos(half_angle),
            normalized_axis[0] * sin_half,
            normalized_axis[1] * sin_half,
            normalized_axis[2] * sin_half
        )

    def norm(self) -> float:
        return math.sqrt(self.w**2 + self.x**2 + self.y**2 + self.z**2)

    def normalize(self):
        n = self.norm() + 1e-12
        return Quaternion(self.w / n, self.x / n, self.y / n, self.z / n)

    def conjugate(self):
        return Quaternion(self.w, -self.x, -self.y, -self.z)

    def multiply(self, q):
        w = self.w * q.w - self.x * q.x - self.y * q.y - self.z * q.z
        x = self.w * q.x + self.x * q.w + self.y * q.z - self.z * q.y
        y = self.w * q.y - self.x * q.z + self.y * q.w + self.z * q.x
        z = self.w * q.z + self.x * q.y - self.y * q.x + self.z * q.w
        return Quaternion(w, x, y, z)

    def rotate_vector(self, v: list[float]) -> list[float]:
        """Applies sandwich product p' = q * p * q* to rotate a 3D vector."""
        p = Quaternion(0, v[0], v[1], v[2])
        q_norm = self.normalize()
        res = q_norm.multiply(p).multiply(q_norm.conjugate())
        return [res.x, res.y, res.z]


class HeighwayDragonMapper:
    """Maps 1D Discrete Sequence Indices into 2D Spatial Fractal Coordinates."""

    @staticmethod
    def get_dragon_coordinate(index: int) -> complex:
        if index == 0:
            return 0 + 0j
        
        bits = bin(index)[2:]
        z = 0 + 0j
        for bit in reversed(bits):
            if bit == '0':
                z = ((1 + 1j) * z) / 2.0
            else:
                z = 1.0 - ((1 - 1j) * z) / 2.0
        return z


class TrochoidalKinematicRouter:
    """Calculates spatial trajectories via Bernoulli-Euler Double Generation Theorem."""

    def __init__(self, P: float, R: float, H: float):
        self.P = P  # Radius of fixed circle
        self.R = R  # Radius of rolling circle
        self.H = H  # Arm length parameter

    def evaluate_position(self, u: float) -> list[float]:
        ratio = (self.P / self.R) + 1.0
        x = (self.P + self.R) * math.cos(u) - self.H * self.R * math.cos(ratio * u)
        y = (self.P + self.R) * math.sin(u) - self.H * self.R * math.sin(ratio * u)
        return [x, y, 0.0]


class FieldExtrapolator:
    """Computes spatial field scale factors using numerical derivatives."""

    @staticmethod
    def compute_local_scaling(func, u: float, eps: float = 1e-6) -> float:
        f_plus = func(u + eps)
        f_minus = func(u - eps)
        
        # Calculate tangent vector / magnitude derivative
        dx = (f_plus[0] - f_minus[0]) / (2.0 * eps)
        dy = (f_plus[1] - f_minus[1]) / (2.0 * eps)
        dz = (f_plus[2] - f_minus[2]) / (2.0 * eps)
        
        return math.sqrt(dx**2 + dy**2 + dz**2)


class GGGEngineCore:
    """Main Orchestrator pipeline for the Garza Global Graviton Project."""

    def __init__(self, P=2.0, R=1.0, H=0.5):
        self.router = TrochoidalKinematicRouter(P, R, H)

    def process_vector_node(self, node_id: int, phase_angle: float) -> dict:
        # 1. Map node ID to 2D Fractal Coordinate
        c_coord = HeighwayDragonMapper.get_dragon_coordinate(node_id)
        
        # 2. Evaluate Trochoidal Path
        base_pos = self.router.evaluate_position(phase_angle)
        
        # 3. Apply Quaternionic Orientation Shift
        rot_axis = [0.0, 0.0, 1.0]
        q_rot = Quaternion.from_axis_angle(rot_axis, phase_angle)
        transformed_pos = q_rot.rotate_vector(base_pos)
        
        # 4. Compute Local Scale Factor via Field Extrapolation
        scaling_factor = FieldExtrapolator.compute_local_scaling(
            lambda angle: q_rot.rotate_vector(self.router.evaluate_position(angle)),
            phase_angle
        )

        return {
            "node_id": node_id,
            "fractal_coordinate": (c_coord.real, c_coord.imag),
            "spatial_vector": transformed_pos,
            "jacobian_scale_factor": scaling_factor
        }


if __name__ == "__main__":
    engine = GGGEngineCore()
    result = engine.process_vector_node(node_id=14, phase_angle=math.pi / 4.0)
    print("--- GGG Engine Output ---")
    print(f"Node ID:               {result['node_id']}")
    print(f"Fractal Mapping (2D):  {result['fractal_coordinate']}")
    print(f"3D Vector Position:    {result['spatial_vector']}")
    print(f"Jacobian Scale Factor: {result['jacobian_scale_factor']:.6f}")