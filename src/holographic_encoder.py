"""AdS/CFT-inspired boundary compression via truncated SVD.

Tactical use: treats a large N-dimensional "bulk" state matrix the way the
AdS/CFT correspondence treats a bulk volume -- as fully reconstructible from
a lower-dimensional "boundary" encoding -- so an edge node can transmit a
compact boundary projection instead of the full bulk tensor.
"""

import numpy as np


class HolographicEncoder:
    """Compresses and reconstructs bulk matrices via variance-truncated SVD."""

    def __init__(self, retained_variance=0.99):
        """Set the fraction of singular-value variance to retain on encode."""
        self.retained_variance = retained_variance

    def encode_bulk_to_boundary(self, bulk_matrix):
        """Compress an N-dimensional bulk state into a boundary via SVD.

        Tactical advantage: sheds redundant bulk data at the edge while
        retaining >=99% of information content, cutting bandwidth for
        mesh/backhaul links without a separate lossy-codec dependency.
        """
        # Perform SVD (Singular Value Decomposition).
        U, S, Vt = np.linalg.svd(bulk_matrix, full_matrices=False)

        # Determine dimension cutoff based on retained variance (information).
        cumulative_variance = np.cumsum(S ** 2) / np.sum(S ** 2)
        cutoff_idx = (
            np.searchsorted(cumulative_variance, self.retained_variance) + 1
        )

        # Truncate to boundary state.
        phi_0_boundary = np.dot(U[:, :cutoff_idx], np.diag(S[:cutoff_idx]))
        projection_tensor = Vt[:cutoff_idx, :]

        retained_size = phi_0_boundary.size + projection_tensor.size
        compression_ratio = 1.0 - retained_size / bulk_matrix.size

        return phi_0_boundary, projection_tensor, compression_ratio

    def decode_boundary_to_bulk(self, phi_0_boundary, projection_tensor):
        """Reconstruct the approximate bulk matrix from its boundary.

        Tactical advantage: lets a receiving node rebuild the full bulk
        state locally instead of requiring the sender to retransmit it.
        """
        return np.dot(phi_0_boundary, projection_tensor)
