import numpy as np

class HolographicEncoder:
    def __init__(self, retained_variance=0.99):
        self.retained_variance = retained_variance

    def encode_bulk_to_boundary(self, bulk_matrix):
        """
        Compresses N-dimensional bulk state into boundary functional phi_0.
        Uses SVD truncation to preserve topological invariants while shedding bulk.
        """
        # Perform SVD (Singular Value Decomposition)
        U, S, Vt = np.linalg.svd(bulk_matrix, full_matrices=False)
        
        # Determine dimension cutoff based on retained variance (information)
        cumulative_variance = np.cumsum(S**2) / np.sum(S**2)
        cutoff_idx = np.searchsorted(cumulative_variance, self.retained_variance) + 1
        
        # Truncate to boundary state
        phi_0_boundary = np.dot(U[:, :cutoff_idx], np.diag(S[:cutoff_idx]))
        projection_tensor = Vt[:cutoff_idx, :]
        
        compression_ratio = 1.0 - (phi_0_boundary.size + projection_tensor.size) / bulk_matrix.size
        
        return phi_0_boundary, projection_tensor, compression_ratio

    def decode_boundary_to_bulk(self, phi_0_boundary, projection_tensor):
        """Reconstructs the bulk theater map at the edge node."""
        return np.dot(phi_0_boundary, projection_tensor)