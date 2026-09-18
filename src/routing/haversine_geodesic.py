"""Vectorized Haversine geodesic distance for long-range flight routing.

Tactical use: great-circle distance on a spherical Earth is required for
any long-range route or target-assignment calculation; the Haversine form
is numerically stable at both very short and near-antipodal ranges, and is
fully vectorizable across large batches of coordinate pairs.
"""

import numpy as np

EARTH_RADIUS_M = 6_371_000.0


class HaversineGeodesicCalculator:
    """Computes great-circle distances between batches of lat/lon pairs."""

    def __init__(self, earth_radius=EARTH_RADIUS_M):
        """Set the spherical Earth radius used for distance scaling."""
        self.earth_radius = earth_radius

    def _calc_central_angle(self, lat1, lon1, lat2, lon2):
        """Evaluate the Haversine central angle shared by both callers.

        Kept private since callers only need distance, not the raw angle.
        """
        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1
        haversine_term = (
            np.sin(delta_lat / 2.0) ** 2
            + np.cos(lat1) * np.cos(lat2) * np.sin(delta_lon / 2.0) ** 2
        )
        return 2.0 * np.arctan2(
            np.sqrt(haversine_term), np.sqrt(1.0 - haversine_term)
        )

    def calc_distance(
        self, latitude_1, longitude_1, latitude_2, longitude_2
    ):
        """Evaluate the Haversine great-circle distance for coordinate pairs.

        Tactical advantage: a single vectorized trig pass resolves route
        distances for an entire batch of origin/destination or
        sensor/target pairs, with no per-pair loop.
        """
        lat1 = np.radians(np.asarray(latitude_1, dtype=float))
        lon1 = np.radians(np.asarray(longitude_1, dtype=float))
        lat2 = np.radians(np.asarray(latitude_2, dtype=float))
        lon2 = np.radians(np.asarray(longitude_2, dtype=float))
        central_angle = self._calc_central_angle(lat1, lon1, lat2, lon2)
        return self.earth_radius * central_angle

    def calc_distance_matrix(
        self, latitudes_a, longitudes_a, latitudes_b, longitudes_b
    ):
        """Compute the full pairwise distance matrix between coordinate sets.

        Tactical advantage: broadcasts one coordinate set against another
        so every sensor/asset can be scored against every candidate
        target/route waypoint in a single vectorized call.
        """
        lat_a = np.radians(np.asarray(latitudes_a, dtype=float))[:, None]
        lon_a = np.radians(np.asarray(longitudes_a, dtype=float))[:, None]
        lat_b = np.radians(np.asarray(latitudes_b, dtype=float))[None, :]
        lon_b = np.radians(np.asarray(longitudes_b, dtype=float))[None, :]
        central_angle = self._calc_central_angle(lat_a, lon_a, lat_b, lon_b)
        return self.earth_radius * central_angle
