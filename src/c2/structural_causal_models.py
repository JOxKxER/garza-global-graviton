"""Linear Structural Causal Model do-operator for counterfactual attribution.

Tactical use: a swarm formation failure correlates with several possible
causes (jamming, hardware fault, operator error), but correlation alone
cannot say which one is the actual root cause. Pearl's do-calculus lets a
C2 engine simulate "if node X's state were forcibly set to x, holding its
causal parents out of the loop, what would downstream nodes look like" --
isolating true causal effect from mere correlation.
"""

import numpy as np


class StructuralCausalModel:
    """Evaluates linear SCM equations and do-operator interventions.

    Models X_i = sum_j W[i, j] * X_j + U_i, where W[i, j] is the causal
    effect of parent j on child i, and U is an exogenous noise/evidence
    term. Observational and interventional states are solved as
    X = (I - W)^-1 @ U.
    """

    def __init__(self, causal_weights):
        """Set the (n, n) structural causal weight matrix W."""
        self.causal_weights = np.asarray(causal_weights, dtype=float)
        self.num_nodes = self.causal_weights.shape[0]

    def solve_observational(self, exogenous_noise):
        """Solve X = (I - W)^-1 @ U for a batch of exogenous noise draws.

        Tactical advantage: a single vectorized linear solve resolves the
        full observed causal state for an entire batch of noisy telemetry
        samples at once.
        """
        u = np.atleast_2d(np.asarray(exogenous_noise, dtype=float))
        identity = np.eye(self.num_nodes)
        structural_matrix = identity - self.causal_weights
        return np.linalg.solve(structural_matrix, u.T).T

    def do_intervene(self, exogenous_noise, intervene_index, intervene_value):
        """Apply do(X_k = x_k): sever k's parent edges, fix its exogenous term.

        Tactical advantage: computes the true counterfactual downstream
        state under a forced root-cause hypothesis (e.g. "if this node
        were jammed to zero output"), separable from the unintervened
        observational baseline for direct causal-effect attribution.
        """
        u = np.atleast_2d(np.asarray(exogenous_noise, dtype=float)).copy()
        u[:, intervene_index] = intervene_value

        w_do = self.causal_weights.copy()
        w_do[intervene_index, :] = 0.0

        identity = np.eye(self.num_nodes)
        structural_matrix = identity - w_do
        intervened_state = np.linalg.solve(structural_matrix, u.T).T

        observational_state = self.solve_observational(exogenous_noise)
        causal_effect = intervened_state - observational_state
        return {
            "intervened_state": intervened_state,
            "observational_state": observational_state,
            "causal_effect": causal_effect,
        }
