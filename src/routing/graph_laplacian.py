"""Graph Laplacian algebraic connectivity for mesh partition early-warning.

Tactical use: the Fiedler eigenvalue (second-smallest eigenvalue of the
graph Laplacian L = D - A) is a single scalar measuring how strongly
connected a network is; it approaches zero exactly as a network is about
to split into disconnected components, giving an early-warning signal
before an EW attack physically fragments the mesh.
"""

import numpy as np
from scipy.linalg import eigvalsh


class GraphLaplacianAnalyzer:
    """Computes the graph Laplacian and its algebraic connectivity."""

    def calc_laplacian(self, adjacency_matrix):
        """Evaluate L = D - A, the degree matrix minus the adjacency matrix.

        Tactical advantage: converts a raw node-connectivity matrix into
        the spectral form needed to quantify mesh robustness in one step.
        """
        adjacency = np.asarray(adjacency_matrix, dtype=float)
        degree = np.diag(np.sum(adjacency, axis=-1))
        return degree - adjacency

    def calc_fiedler_value(self, adjacency_matrix):
        """Evaluate the Fiedler value, the 2nd-smallest Laplacian eigenvalue.

        Tactical advantage: a single scalar early-warning metric for mesh
        fragmentation risk; a value near zero means the network is close
        to splitting into two or more disconnected partitions.
        """
        laplacian = self.calc_laplacian(adjacency_matrix)
        eigenvalues = eigvalsh(laplacian)
        return float(np.sort(eigenvalues)[1])

    def assess_partition_risk(self, adjacency_matrix, risk_threshold=0.5):
        """Flag whether the mesh's Fiedler value has fallen below a safe floor.

        Tactical advantage: converts the raw Fiedler value into an
        operator-actionable partition-risk flag for automated mesh-repair
        triggers (e.g. relay repositioning).
        """
        fiedler_value = self.calc_fiedler_value(adjacency_matrix)
        return {
            "fiedler_value": fiedler_value,
            "partition_risk": fiedler_value < risk_threshold,
        }
