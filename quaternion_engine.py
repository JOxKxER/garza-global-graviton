import numpy as np

class QuaternionVectorEngine:
    def __init__(self):
        self.origin = np.array([0.0, 0.0, 0.0, 1.0])

    def normalize_quaternion(self, q):
        norm = np.linalg.norm(q)
        if norm == 0:
            return q
        return q / norm

    def apply_quaternion_rotation(self, vector_3d, rotation_angles_rad):
        pitch, yaw, roll = rotation_angles_rad
        
        cy = np.cos(yaw * 0.5)
        sy = np.sin(yaw * 0.5)
        cp = np.cos(pitch * 0.5)
        sp = np.sin(pitch * 0.5)
        cr = np.cos(roll * 0.5)
        sr = np.sin(roll * 0.5)

        qw = cr * cp * cy + sr * sp * sy
        qx = sr * cp * cy - cr * sp * sy
        qy = cr * sp * cy + sr * cp * sy
        qz = cr * cp * sy - sr * sp * cy

        q = self.normalize_quaternion(np.array([qx, qy, qz, qw]))

        x, y, z = vector_3d
        transformed_vector = [
            round(x * q[3] + y * q[2] - z * q[1], 4),
            round(y * q[3] + z * q[0] - x * q[2], 4),
            round(z * q[3] + x * q[1] - y * q[0], 4)
        ]

        return {
            "status": "success",
            "quaternion_vector_w_xyz": [round(val, 4) for val in q.tolist()],
            "transformed_spatial_coordinates": transformed_vector,
            "manifold_projection": "Stable 4D Toroidal Field"
        }