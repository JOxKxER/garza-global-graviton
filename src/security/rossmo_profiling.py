"""Rossmo's geographic profiling for adversarial origin-point estimation.

Tactical use: scattered kinetic or cyber detection events (attack sites,
intrusion beacons) rarely occur exactly at an adversary's launch/staging
point. Rossmo's formula combines a near-field "buffer zone" (attackers
avoid acting too close to their base) with a far-field distance-decay term
to produce a 2D probability surface over candidate origin locations.
"""

import numpy as np

from src.utils.math_utils import pairwise_euclidean_distance

DEFAULT_BUFFER_RADIUS = 0.3
DEFAULT_DISTANCE_DECAY_EXPONENT = 1.2


class RossmoProfiler:
    """Computes a 2D geographic profile surface from scattered detections."""

    def __init__(
        self,
        buffer_radius=DEFAULT_BUFFER_RADIUS,
        decay_exponent=DEFAULT_DISTANCE_DECAY_EXPONENT,
    ):
        """Set the buffer-zone radius B and the distance-decay exponent f/g."""
        self.buffer_radius = buffer_radius
        self.decay_exponent = decay_exponent

    def calc_probability_surface(
        self, candidate_x, candidate_y, detection_points
    ):
        """Evaluate the Rossmo profile score at every candidate origin cell.

        For each candidate cell and each detection point, sums either the
        far-field decay term phi/distance^f (outside the buffer zone) or
        the near-field buffer term (1-phi)*B^(g-f)/(2B-distance)^g (inside
        the buffer zone), matching the standard Rossmo formulation.

        Tactical advantage: a single broadcasted pass scores an entire
        candidate-origin grid against all detection events at once,
        producing a ranked map of likely adversarial staging areas.
        """
        candidate_x = np.asarray(candidate_x, dtype=float)
        candidate_y = np.asarray(candidate_y, dtype=float)
        detections = np.asarray(detection_points, dtype=float)

        grid_points = np.stack(
            [candidate_x.ravel(), candidate_y.ravel()], axis=-1
        )
        flat_distance = pairwise_euclidean_distance(grid_points, detections)
        distance = flat_distance.reshape(
            candidate_x.shape + (detections.shape[0],)
        )

        buffer_radius = self.buffer_radius
        exponent = self.decay_exponent
        outside_buffer = distance > buffer_radius

        far_field_term = 1.0 / (distance ** exponent)
        near_field_denominator = np.clip(
            2.0 * buffer_radius - distance, 1e-6, None
        )
        near_field_term = (
            buffer_radius ** (2.0 * exponent - exponent)
        ) / (near_field_denominator ** exponent)

        contribution = np.where(
            outside_buffer, far_field_term, near_field_term
        )
        return np.sum(contribution, axis=-1)

    def find_most_likely_origin(
        self, candidate_x, candidate_y, detection_points
    ):
        """Return the candidate coordinate with the highest profile score.

        Tactical advantage: collapses the full probability surface into a
        single actionable "most likely staging area" recommendation.
        """
        surface = self.calc_probability_surface(
            candidate_x, candidate_y, detection_points
        )
        best_index = np.unravel_index(np.argmax(surface), surface.shape)
        return {
            "best_index": best_index,
            "best_x": candidate_x[best_index],
            "best_y": candidate_y[best_index],
            "score": float(surface[best_index]),
        }
