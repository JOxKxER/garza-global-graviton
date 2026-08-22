import pytest
from pathlib import Path
from src.benchmark import run_scaling_benchmark, plot_benchmark_results

def test_run_scaling_benchmark():
    sizes = [100, 500, 1000]
    results = run_scaling_benchmark(array_sizes=sizes, iterations=2)
    assert "sizes" in results
    assert "latencies_ms" in results
    assert len(results["latencies_ms"]) == len(sizes)
    assert all(t > 0 for t in results["latencies_ms"])

def test_plot_benchmark_results(tmp_path):
    results = {
        "sizes": [100, 1000],
        "latencies_ms": [0.05, 0.45]
    }
    plot_file = tmp_path / "benchmark_test.png"
    out_path = plot_benchmark_results(results, output_image=plot_file)
    assert out_path.exists()
    assert out_path.stat().st_size > 0
