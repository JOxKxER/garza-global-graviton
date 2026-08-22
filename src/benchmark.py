import time
import logging
from pathlib import Path
from typing import List, Dict, Union
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.core import process_vector_data

logger = logging.getLogger(__name__)

def run_scaling_benchmark(
    array_sizes: List[int] = [1_000, 10_000, 100_000, 500_000, 1_000_000, 5_000_000],
    iterations: int = 5
) -> Dict[str, Union[List[int], List[float]]]:
    """
    Measures execution time of process_vector_data across increasing array sizes.
    """
    logger.info(f"Starting benchmark across {len(array_sizes)} sizes with {iterations} iterations each.")
    avg_times_ms: List[float] = []

    for size in array_sizes:
        # Generate synthetic float array
        test_array = np.random.rand(size).astype(np.float64)
        run_times = []

        for _ in range(iterations):
            start = time.perf_counter()
            _ = process_vector_data(test_array, scale_factor=2.0)
            elapsed = time.perf_counter() - start
            run_times.append(elapsed * 1000.0)  # Convert to milliseconds

        avg_ms = float(np.mean(run_times))
        avg_times_ms.append(avg_ms)
        logger.info(f"Array Size: {size:>10,d} | Avg Latency: {avg_ms:8.3f} ms")

    return {
        "sizes": array_sizes,
        "latencies_ms": avg_times_ms
    }

def plot_benchmark_results(
    results: Dict[str, Union[List[int], List[float]]],
    output_image: Union[str, Path] = "output/benchmark_scaling.png"
) -> Path:
    """
    Generates a log-log scale benchmark performance plot.
    """
    path = Path(output_image)
    path.parent.mkdir(parents=True, exist_ok=True)

    sizes = results["sizes"]
    times = results["latencies_ms"]

    fig, ax = plt.subplots(figsize=(8.5, 5), dpi=130)
    ax.plot(sizes, times, marker="o", linewidth=2, color="#d62728", label="NumPy Vectorized Pipeline")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_title("Vector Processing Latency vs Array Size", fontsize=13, pad=12)
    ax.set_xlabel("Array Size (Number of Elements - Log Scale)", fontsize=10)
    ax.set_ylabel("Execution Time (ms - Log Scale)", fontsize=10)
    ax.grid(True, which="both", linestyle="--", alpha=0.5)
    ax.legend(loc="upper left")

    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)

    logger.info(f"Benchmark chart saved to: {path}")
    return path
