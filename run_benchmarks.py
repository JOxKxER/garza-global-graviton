import time
import numpy as np

# Import your modules
from dirac_algebra import DiracAlgebra
from ptolemaic_validator import PtolemaicValidator
from lambda_cdm_engine import LambdaCDMController
from holographic_encoder import HolographicEncoder
from tcuft_conformal import TCUFTEngine

def run_all_benchmarks():
    print("--- STARTING GGG BENCHMARKS ---\n")

    # 1. Dirac Algebra Benchmark
    start = time.perf_counter()
    dirac = DiracAlgebra()
    psi_L, psi_R = np.random.rand(2) + 1j, np.random.rand(2) + 1j
    bispinor = dirac.generate_bispinor(psi_L, psi_R)
    dirac.check_invariants()
    print(f"[OK] Dirac Spinor Generation: {(time.perf_counter() - start) * 1000:.4f} ms")

    # 2. Ptolemaic Validator Benchmark
    start = time.perf_counter()
    validator = PtolemaicValidator()
    # Create a dummy signal with 1000 data points
    dummy_signal = np.sin(2 * np.pi * 5 * np.linspace(0, 1, 1000)) + np.random.normal(0, 0.1, 1000)
    result = validator.evaluate_signal(dummy_signal)
    print(f"[OK] Ptolemaic Spoofing Filter: {(time.perf_counter() - start) * 1000:.4f} ms")

    # 3. Lambda-CDM Benchmark
    start = time.perf_counter()
    cdm = LambdaCDMController()
    radius = cdm.calc_turnaround_radius(swarm_mass_M=5000)
    print(f"[OK] Lambda-CDM Swarm Turnaround: {(time.perf_counter() - start) * 1000:.4f} ms")

    # 4. AdS/CFT Holographic Encoder Benchmark
    start = time.perf_counter()
    encoder = HolographicEncoder()
    dummy_bulk_matrix = np.random.rand(100, 100)
    boundary, projection, compression = encoder.encode_bulk_to_boundary(dummy_bulk_matrix)
    print(f"[OK] Holographic Compression ({compression*100:.1f}%): {(time.perf_counter() - start) * 1000:.4f} ms")

    # 5. TCUFT Conformal Benchmark
    start = time.perf_counter()
    tcuft = TCUFTEngine()
    scaled_metric = tcuft.conformal_transformation(omega_scale_factor=2.5)
    print(f"[OK] TCUFT Metric Scaling: {(time.perf_counter() - start) * 1000:.4f} ms")
    
    print("\n--- BENCHMARKS COMPLETE ---")

if __name__ == "__main__":
    run_all_benchmarks()