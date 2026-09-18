"""Navier-Stokes-inspired congestion field for dynamic mesh packet rerouting.

Tactical use: treats network mesh traffic load as a continuous fluid on a
2D grid of nodes/links rather than as discrete per-packet routing decisions,
so a single vectorized pressure-gradient step yields reroute vectors for the
entire mesh at once instead of per-flow shortest-path recomputation.
"""

import numpy as np


class FluidRoutingEngine:
    """Advects a congestion field under a simplified incompressible N-S step.
    (See class docstring continuation below for the governing equation.)

    Models congestion as density rho and traffic flow as velocity field u on
    a grid, evolving:
        rho*(du/dt + u.grad(u)) = -grad(p) + mu*laplacian(u)
    where pressure p stands in for queue backpressure at each node.
    """

    def __init__(self, viscosity_mu=0.1, fluid_density_rho=1.0):
        """Set the viscosity (reroute damping) and density (stiffness)."""
        self.mu = viscosity_mu
        self.rho = fluid_density_rho

    def _laplacian(self, field):
        """Compute the discrete 2D Laplacian via vectorized neighbor diffs."""
        return (
            np.roll(field, 1, axis=0)
            + np.roll(field, -1, axis=0)
            + np.roll(field, 1, axis=1)
            + np.roll(field, -1, axis=1)
            - 4 * field
        )

    def _gradient(self, field):
        """Compute the 2D gradient (dfield/dx, dfield/dy) via central diffs."""
        grad_x = (np.roll(field, -1, axis=0) - np.roll(field, 1, axis=0)) / 2.0
        grad_y = (np.roll(field, -1, axis=1) - np.roll(field, 1, axis=1)) / 2.0
        return grad_x, grad_y

    def step_congestion_field(self, velocity_u, velocity_v, pressure, dt=0.01):
        """Advance the mesh congestion velocity field by one N-S time step.

        Tactical advantage: produces per-node reroute vectors (u, v) for an
        entire mesh in one vectorized pass, letting an edge controller shed
        congestion toward low-pressure (low-backpressure) links in real time.
        """
        laplacian_u = self._laplacian(velocity_u)
        laplacian_v = self._laplacian(velocity_v)
        pressure_grad_x, pressure_grad_y = self._gradient(pressure)

        advection_u = velocity_u * self._gradient(velocity_u)[0]
        advection_v = velocity_v * self._gradient(velocity_v)[1]

        new_u = velocity_u + dt * (
            -advection_u - pressure_grad_x / self.rho
            + (self.mu / self.rho) * laplacian_u
        )
        new_v = velocity_v + dt * (
            -advection_v - pressure_grad_y / self.rho
            + (self.mu / self.rho) * laplacian_v
        )
        return new_u, new_v

    def compute_reroute_vectors(self, congestion_field):
        """Derive normalized reroute vectors that flow away from congestion.

        Tactical advantage: a single gradient-descent-style computation gives
        every node a "route away from here" vector proportional to local
        congestion pressure, avoiding a full per-flow routing table rebuild.
        """
        grad_x, grad_y = self._gradient(congestion_field)
        magnitude = np.sqrt(grad_x ** 2 + grad_y ** 2)
        safe_magnitude = np.where(magnitude == 0, 1.0, magnitude)
        return -grad_x / safe_magnitude, -grad_y / safe_magnitude
