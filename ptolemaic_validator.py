import numpy as np

class PtolemaicValidator:
    def __init__(self, complexity_threshold=5, power_threshold=0.05):
        self.complexity_threshold = complexity_threshold
        self.power_threshold = power_threshold

    def evaluate_signal(self, telemetry_signal, dt=0.01):
        """
        Decomposes signal into harmonic epicycles. 
        Flags signal if it requires too many nested epicycles (over-fitting).
        """
        N = len(telemetry_signal)
        # Perform Fast Fourier Transform
        fft_values = np.fft.fft(telemetry_signal)
        frequencies = np.fft.fftfreq(N, d=dt)
        
        # Calculate Power Spectral Density
        power = np.abs(fft_values)**2 / N
        max_power = np.max(power)
        
        # Count significant harmonics (epicycles)
        significant_harmonics = np.sum(power > (self.power_threshold * max_power))
        
        is_synthetic = significant_harmonics > self.complexity_threshold
        
        return {
            "epicycle_count": significant_harmonics,
            "is_synthetic_spoof": is_synthetic,
            "confidence": 1.0 - (self.complexity_threshold / max(significant_harmonics, 1))
        }