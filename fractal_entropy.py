import math
from collections import Counter

class FractalEntropyProcessor:
    def __init__(self):
        pass

    def calculate_shannon_entropy(self, data_stream):
        """
        Calculates the Shannon Entropy (information density) of a given data stream.
        High entropy indicates dense, incompressible, or potentially encrypted/jammed data.
        """
        if not data_stream:
            return 0.0
        
        entropy = 0
        length = len(data_stream)
        frequencies = Counter(data_stream)
        
        for freq in frequencies.values():
            probability = freq / length
            entropy -= probability * math.log2(probability)
            
        return round(entropy, 4)

    def menger_sponge_scattering(self, iterations, base_volume=1.0):
        """
        Simulates RF signal scattering across a complex aerospace surface 
        using Menger Sponge fractal volume degradation.
        """
        # Volume of a Menger Sponge after n iterations is V_0 * (20/27)^n
        volume_ratio = (20.0 / 27.0) ** iterations
        remaining_volume = base_volume * volume_ratio
        
        return round(remaining_volume, 6)

    def process_signal(self, telemetry_data, fractal_depth=3):
        """Processes the stream to evaluate information density and physical signal scatter."""
        entropy_score = self.calculate_shannon_entropy(telemetry_data)
        scattering_vol = self.menger_sponge_scattering(fractal_depth)
        
        analysis = "Stable, compressible signal."
        if entropy_score > 3.8:
            analysis = "High density. Potential encryption or noise jamming detected."
            
        return {
            "status": "success",
            "telemetry_entropy_bits": entropy_score,
            "fractal_depth_iterations": fractal_depth,
            "menger_sponge_volume_ratio": scattering_vol,
            "signal_analysis": analysis
        }