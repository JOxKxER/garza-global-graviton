import numpy as np

class LambdaCDMController:
    def __init__(self, H0=70.0, Omega_m=0.3, Omega_Lambda=0.7, G=6.67430e-11):
        self.H0 = H0
        self.Omega_m = Omega_m
        self.Omega_Lambda = Omega_Lambda
        self.G = G

    def calc_friedmann_expansion(self, scale_factor_a):
        """Calculates dynamic theater expansion rate H(a)."""
        a = scale_factor_a
        # H^2(a) = H0^2 [Omega_m * a^-3 + Omega_Lambda]
        H_squared = (self.H0**2) * (self.Omega_m * (a**-3) + self.Omega_Lambda)
        return np.sqrt(H_squared)

    def calc_turnaround_radius(self, swarm_mass_M):
        """
        Calculates the boundary where local swarm cohesion is perfectly 
        balanced against wide-area repulsive expansion.
        """
        # r = (G * M / (H0^2 * Omega_Lambda))^(1/3)
        numerator = self.G * swarm_mass_M
        denominator = (self.H0**2) * self.Omega_Lambda
        r_turnaround = np.cbrt(numerator / denominator)
        return r_turnaround