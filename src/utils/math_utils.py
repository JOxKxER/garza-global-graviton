"""Centralized numerically-stable vectorized math primitives.

Tactical use: several GGG modules (attention filters, policy distillation,
spatial guidance, sensor assignment, geographic profiling) each need the
same two numerically-stable building blocks -- a stable softmax and a
broadcasting pairwise Euclidean distance -- so they are implemented once
here instead of being duplicated with subtly different edge-case handling
per module.
"""

import numpy as np

DEFAULT_DISTANCE_EPSILON = 1e-9


def softmax(scores, axis=-1):
    """Evaluate a numerically stable softmax over the given axis.

    Tactical advantage: shifting by the per-axis max before exponentiating
    prevents overflow on large logits, giving every caller (attention
    filters, policy losses, distillation) the same safe normalization.
    """
    values = np.asarray(scores, dtype=float)
    shifted = values - np.max(values, axis=axis, keepdims=True)
    exponentials = np.exp(shifted)
    return exponentials / np.sum(exponentials, axis=axis, keepdims=True)


def pairwise_euclidean_distance(
    points_a, points_b, epsilon=DEFAULT_DISTANCE_EPSILON
):
    """Compute the broadcasting (M, N) pairwise Euclidean distance matrix.

    Accepts (M, D) and (N, D) coordinate arrays and returns the distance
    between every row of `points_a` and every row of `points_b`. A small
    epsilon floor is applied so a zero distance (coincident points) never
    produces a division-by-zero in a caller that takes a reciprocal.

    Tactical advantage: one vectorized broadcast-and-norm implementation
    shared by every spatial/assignment/profiling module, so distance-matrix
    edge cases (exact coordinate collisions) are handled consistently
    everywhere instead of once per caller.
    """
    a = np.atleast_2d(np.asarray(points_a, dtype=float))
    b = np.atleast_2d(np.asarray(points_b, dtype=float))
    diff = a[:, None, :] - b[None, :, :]
    distance = np.linalg.norm(diff, axis=-1)
    return np.maximum(distance, epsilon)
