"""Damped Least Squares inverse kinematics for singularity-free tracking.

Tactical use: a directed-energy effector (e.g. laser dazzler) gimbal that
uses a naive pseudoinverse Jacobian solver produces unbounded joint-rate
commands near a kinematic singularity, causing violent slew or gimbal lock
mid-track. Adding a damping term trades a small amount of tracking accuracy
near singularities for guaranteed-bounded, stable joint commands.
"""

import numpy as np

DEFAULT_DAMPING_FACTOR = 0.05


class DampedLeastSquaresSolver:
    """Solves damped-least-squares inverse kinematics for batched Jacobians."""

    def __init__(self, damping_factor=DEFAULT_DAMPING_FACTOR):
        """Set the damping factor lambda controlling singularity robustness."""
        self.damping_factor = damping_factor

    def calc_joint_velocities(self, jacobians, cartesian_velocities):
        """Evaluate qdot = J^T (J J^T + lambda^2 I)^-1 xdot for a batch.

        Tactical advantage: a single batched matrix-inverse pass computes
        stable joint-rate commands for an entire fleet of gimbals/arms at
        once, remaining well-conditioned even as individual arms pass
        through their own kinematic singularities.
        """
        j = np.atleast_3d(jacobians)
        if j.ndim == 2:
            j = j[None, :, :]
        xdot = np.atleast_2d(cartesian_velocities)

        _, task_dim, _ = j.shape
        identity = np.eye(task_dim)
        damping_term = (self.damping_factor ** 2) * identity

        j_transpose = np.transpose(j, (0, 2, 1))
        gramian = np.matmul(j, j_transpose) + damping_term[None, :, :]
        inverse_gramian = np.linalg.inv(gramian)

        pseudo_jacobian = np.matmul(j_transpose, inverse_gramian)
        return np.einsum("nij,nj->ni", pseudo_jacobian, xdot)

    def calc_manipulability(self, jacobians):
        """Evaluate sqrt(det(J J^T)), a scalar distance-from-singularity score.

        Tactical advantage: lets a controller preemptively slow a track
        maneuver before the damping term is forced to trade away accuracy.
        """
        j = np.atleast_3d(jacobians)
        if j.ndim == 2:
            j = j[None, :, :]
        j_transpose = np.transpose(j, (0, 2, 1))
        gramian = np.matmul(j, j_transpose)
        return np.sqrt(np.clip(np.linalg.det(gramian), 0.0, None))
