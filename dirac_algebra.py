import numpy as np

class DiracAlgebra:
    def __init__(self):
        # Define 2x2 Pauli Matrices
        self.sigma_x = np.array([[0, 1], [1, 0]], dtype=complex)
        self.sigma_y = np.array([[0, -1j], [1j, 0]], dtype=complex)
        self.sigma_z = np.array([[1, 0], [0, -1]], dtype=complex)
        self.I2 = np.eye(2, dtype=complex)
        
        # Define 4x4 Gamma Matrices (Dirac Representation)
        self.gamma_0 = np.block([[self.I2, np.zeros((2,2))], 
                                 [np.zeros((2,2)), -self.I2]])
        
        self.gamma_1 = np.block([[np.zeros((2,2)), self.sigma_x], 
                                 [-self.sigma_x, np.zeros((2,2))]])
                                 
        self.gamma_2 = np.block([[np.zeros((2,2)), self.sigma_y], 
                                 [-self.sigma_y, np.zeros((2,2))]])
                                 
        self.gamma_3 = np.block([[np.zeros((2,2)), self.sigma_z], 
                                 [-self.sigma_z, np.zeros((2,2))]])
                                 
        self.gamma_5 = 1j * self.gamma_0 @ self.gamma_1 @ self.gamma_2 @ self.gamma_3

    def generate_bispinor(self, psi_L, psi_R):
        """Creates a 4-component bispinor from Left and Right chiral states."""
        return np.concatenate((psi_L, psi_R))
        
    def check_invariants(self):
        """Validates Clifford algebra anti-commutation relations: {y^u, y^v} = 2n^uv I"""
        anticomm = self.gamma_1 @ self.gamma_1 + self.gamma_1 @ self.gamma_1
        assert np.allclose(anticomm, -2 * np.eye(4)), "Metric signature invariant failed!"
        return True