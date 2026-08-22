import logging
import numpy as np
from src.core import calculate_shannon_entropy, calculate_spectral_entropy, compute_power_spectral_density

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

fs = 500.0
t = np.linspace(0, 1.0, int(fs), endpoint=False)

# Synthesize a multi-harmonic signal mixed with Gaussian noise
carrier = np.sin(2 * np.pi * 15.0 * t) + 0.5 * np.sin(2 * np.pi * 45.0 * t)
noise = 0.2 * np.random.randn(len(t))
signal = carrier + noise

shannon_bits = calculate_shannon_entropy(signal, bins=32)
spec_entropy = calculate_spectral_entropy(signal, sampling_rate=fs)
freqs, psd = compute_power_spectral_density(signal, sampling_rate=fs)

logging.info(f"Signal Samples: {len(signal)}")
logging.info(f"Shannon Entropy: {shannon_bits:.3f} bits")
logging.info(f"Spectral Entropy: {spec_entropy:.3f} [0=Pure Tone, 1=White Noise]")
logging.info(f"Dominant Spectral Peak: {freqs[np.argmax(psd)]:.1f} Hz")
