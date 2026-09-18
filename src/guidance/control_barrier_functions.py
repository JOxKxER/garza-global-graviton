"""Control Barrier Functions enforcing hard physical safety envelopes.

Tactical use: a reinforcement-learned or otherwise opaque policy can
propose actions that are tactically clever but physically unsafe (e.g.
below minimum altitude, on a collision course). A Control Barrier Function
provides an independently verifiable, model-based check that filters or
flags any action violating a hard survival constraint, regardless of what
the learned policy recommends.
"""

import numpy as np

DEFAULT_CLASS_K_GAIN = 1.0


class ControlBarrierFunction:
    """Evaluates CBF safety conditions L_f h + L_g h * u + alpha(h) >= 0."""

    def __init__(self, class_k_gain=DEFAULT_CLASS_K_GAIN):
        """Set alpha's linear class-K gain (alpha(h) = gain * h)."""
        self.class_k_gain = class_k_gain

    def calc_lie_derivatives(self, barrier_gradient, drift_dynamics):
        """Evaluate L_f h(x) = grad(h) . f(x) for a batch of states.

        Tactical advantage: vectorized over an entire batch of live
        platform states, giving the unforced (drift-only) rate of change
        of the safety margin for every agent at once.
        """
        grad_h = np.atleast_2d(barrier_gradient)
        f_x = np.atleast_2d(drift_dynamics)
        return np.sum(grad_h * f_x, axis=-1)

    def calc_control_effect(
        self, barrier_gradient, control_matrix, control_input
    ):
        """Evaluate L_g h(x) * u = grad(h) . (g(x) @ u) for a batch of states.

        Tactical advantage: quantifies exactly how much a proposed control
        action moves the safety margin, before that action is applied.
        """
        grad_h = np.atleast_2d(barrier_gradient)
        g_x = np.atleast_3d(control_matrix)
        u = np.atleast_2d(control_input)
        control_effect = np.einsum("nij,nj->ni", g_x, u)
        return np.sum(grad_h * control_effect, axis=-1)

    def is_action_safe(
        self,
        barrier_value,
        barrier_gradient,
        drift_dynamics,
        control_matrix,
        control_input,
    ):
        """Evaluate the full CBF condition for a batch of proposed actions.

        Tactical advantage: a single vectorized safety gate that can veto
        or flag any AI-generated action across an entire swarm before
        execution, independent of how that action was originally decided.
        """
        h = np.atleast_1d(np.asarray(barrier_value, dtype=float))
        lie_f = self.calc_lie_derivatives(barrier_gradient, drift_dynamics)
        lie_g_u = self.calc_control_effect(
            barrier_gradient, control_matrix, control_input
        )
        constraint_value = lie_f + lie_g_u + self.class_k_gain * h
        return {
            "constraint_value": constraint_value,
            "is_safe": constraint_value >= 0.0,
        }
