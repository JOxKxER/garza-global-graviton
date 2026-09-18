"""Runs GGG validation simulations and compiles a PDF summary report.

Executes a multi-threaded Zero-Copy Buffer Pool concurrency stress test,
times the Mori-Zwanzig kernel deconvolution and tautochrone priority
scheduler in isolation, captures the full 64-module master benchmark
suite (`run_benchmarks.py`), and writes all results into a formatted
PDF report on the desktop via `reportlab`.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.memory.zero_copy_buffer import ZeroCopyBufferPool
from src.physics.mori_zwanzig_kernel import MoriZwanzigKernelEstimator
from src.scheduling.cycloid_priority_queue import (
    TautochronePriorityScheduler,
)

REPO_ROOT = Path(__file__).resolve().parent
BENCHMARK_LINE_PATTERN = re.compile(
    r"^\[OK\] (?P<name>.+): (?P<ms>[\d.]+) ms$"
)


@dataclass
class StressTestResult:
    """Outcome of the zero-copy buffer pool concurrency stress test."""

    num_threads: int
    cycles_per_thread: int
    total_operations: int
    total_seconds: float
    errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if no worker thread raised or reported a corruption error."""
        return not self.errors


def run_zero_copy_stress_test(
    num_threads: int = 8, cycles_per_thread: int = 500
) -> StressTestResult:
    """Hammer one shared ZeroCopyBufferPool from many threads concurrently.

    Each worker repeatedly allocates a buffer, writes a thread-unique
    byte pattern into it, verifies the pattern reads back unchanged, and
    frees the buffer -- exercising the pool's lock-protected free-list
    allocator under real concurrent contention.
    """
    pool = ZeroCopyBufferPool(pool_size_bytes=1 << 20)
    errors: list[str] = []
    errors_lock = threading.Lock()

    def worker(thread_index: int) -> None:
        pattern = bytes([thread_index % 256]) * 64
        for _ in range(cycles_per_thread):
            try:
                handle = pool.allocate(64)
                handle.view[:] = pattern
                if bytes(handle.view) != pattern:
                    raise RuntimeError("buffer content corrupted")
                pool.free(handle)
            except Exception as error:  # noqa: BLE001 - report, don't crash
                with errors_lock:
                    errors.append(f"thread {thread_index}: {error}")

    threads = [
        threading.Thread(target=worker, args=(index,))
        for index in range(num_threads)
    ]

    start = time.perf_counter()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    total_seconds = time.perf_counter() - start

    pool.close()

    return StressTestResult(
        num_threads=num_threads,
        cycles_per_thread=cycles_per_thread,
        total_operations=num_threads * cycles_per_thread,
        total_seconds=total_seconds,
        errors=errors,
    )


def run_mori_zwanzig_benchmark() -> float:
    """Time one Mori-Zwanzig kernel deconvolution, return elapsed ms."""
    time_step = 0.05
    time_axis = np.arange(200) * time_step
    autocorrelation = np.exp(-time_axis / 1.5)
    true_kernel = 4.0 * np.exp(-time_axis / 0.4)

    estimator = MoriZwanzigKernelEstimator(time_step=time_step)
    start = time.perf_counter()
    derivative = estimator.convolve_kernel(true_kernel, autocorrelation)
    estimator.estimate_kernel(autocorrelation, derivative)
    return (time.perf_counter() - start) * 1000.0


def run_tautochrone_scheduler_benchmark() -> float:
    """Time enqueue/dequeue of 1,000 tasks and return elapsed milliseconds."""
    scheduler = TautochronePriorityScheduler()
    urgency_radii = np.random.default_rng(0).uniform(0.05, 50.0, 1000)

    start = time.perf_counter()
    for index, radius in enumerate(urgency_radii):
        scheduler.enqueue(f"task-{index}", float(radius))
    while len(scheduler) > 0:
        scheduler.dequeue()
    return (time.perf_counter() - start) * 1000.0


def run_master_benchmark_suite() -> list[tuple[str, float]]:
    """Run run_benchmarks.py as a subprocess and parse each module's timing.

    Tactical advantage: reuses the exact, already-verified benchmark
    script as the source of truth instead of re-implementing per-module
    timing logic, so the report always reflects the real suite output.
    """
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "run_benchmarks.py")],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )

    timings: list[tuple[str, float]] = []
    for line in result.stdout.splitlines():
        match = BENCHMARK_LINE_PATTERN.match(line.strip())
        if match:
            timings.append((match.group("name"), float(match.group("ms"))))
    return timings


def build_pdf_report(
    output_path: Path,
    stress_result: StressTestResult,
    mori_zwanzig_ms: float,
    tautochrone_ms: float,
    module_timings: list[tuple[str, float]],
) -> None:
    """Render every captured metric into a formatted PDF at output_path."""
    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )
    story = []

    story.append(Paragraph("GGG Framework Validation Report", styles["Title"]))
    story.append(
        Paragraph(
            "Garza Global Graviton (GGG) edge-compute engine -- "
            "performance and memory validation simulation results.",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.25 * inch))

    story.append(
        Paragraph(
            "1. Zero-Copy Buffer Pool Stress Test", styles["Heading2"]
        )
    )
    throughput = stress_result.total_operations / stress_result.total_seconds
    stress_rows = [
        ["Metric", "Value"],
        ["Worker threads", str(stress_result.num_threads)],
        ["Cycles per thread", str(stress_result.cycles_per_thread)],
        ["Total operations", str(stress_result.total_operations)],
        ["Total elapsed time", f"{stress_result.total_seconds:.4f} s"],
        ["Throughput", f"{throughput:,.0f} ops/s"],
        ["Status", "PASSED" if stress_result.passed else "FAILED"],
    ]
    story.append(_build_table(stress_rows))
    if not stress_result.passed:
        story.append(Spacer(1, 0.1 * inch))
        for error in stress_result.errors[:10]:
            story.append(Paragraph(error, styles["Code"]))
    story.append(Spacer(1, 0.25 * inch))

    story.append(
        Paragraph("2. Isolated Module Benchmarks", styles["Heading2"])
    )
    isolated_rows = [
        ["Module", "Execution Time"],
        [
            "Mori-Zwanzig Memory Kernel (deconvolution)",
            f"{mori_zwanzig_ms:.4f} ms",
        ],
        [
            "Tautochrone Priority Scheduler (1,000 tasks)",
            f"{tautochrone_ms:.4f} ms",
        ],
    ]
    story.append(_build_table(isolated_rows))
    story.append(Spacer(1, 0.25 * inch))

    story.append(
        Paragraph(
            f"3. Master Benchmark Suite ({len(module_timings)} Modules)",
            styles["Heading2"],
        )
    )
    suite_rows = [["#", "Module", "Execution Time (ms)"]]
    for index, (name, ms) in enumerate(module_timings, start=1):
        suite_rows.append([str(index), name, f"{ms:.4f}"])
    suite_col_widths = [0.4 * inch, 4.2 * inch, 1.4 * inch]
    story.append(_build_table(suite_rows, col_widths=suite_col_widths))
    story.append(Spacer(1, 0.25 * inch))

    total_suite_ms = sum(ms for _, ms in module_timings)
    summary_rows = [
        ["Metric", "Value"],
        ["Modules executed", str(len(module_timings))],
        ["Total suite execution time", f"{total_suite_ms:.4f} ms"],
        ["Stress test status", "PASSED" if stress_result.passed else "FAILED"],
    ]
    story.append(Paragraph("4. Summary", styles["Heading2"]))
    story.append(_build_table(summary_rows))

    document.build(story)


def _build_table(
    rows: list[list[str]], col_widths: list[float] | None = None
) -> Table:
    """Build a consistently styled reportlab Table from a list of rows."""
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.whitesmoke, colors.white],
                ),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def main() -> None:
    """Run all simulations and write the PDF report to the desktop."""
    print("Running Zero-Copy Buffer Pool concurrency stress test...")
    stress_result = run_zero_copy_stress_test()
    print(
        f"  {stress_result.total_operations} operations in "
        f"{stress_result.total_seconds:.4f}s "
        f"({'PASSED' if stress_result.passed else 'FAILED'})"
    )

    print("Running Mori-Zwanzig memory kernel benchmark...")
    mori_zwanzig_ms = run_mori_zwanzig_benchmark()
    print(f"  {mori_zwanzig_ms:.4f} ms")

    print("Running Tautochrone priority scheduler benchmark...")
    tautochrone_ms = run_tautochrone_scheduler_benchmark()
    print(f"  {tautochrone_ms:.4f} ms")

    print("Running the full 64-module master benchmark suite...")
    module_timings = run_master_benchmark_suite()
    print(f"  Captured {len(module_timings)} module timings")

    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    os.makedirs(desktop_path, exist_ok=True)
    output_path = Path(desktop_path) / "1st Test.pdf"

    print(f"Writing PDF report to {output_path} ...")
    build_pdf_report(
        output_path,
        stress_result,
        mori_zwanzig_ms,
        tautochrone_ms,
        module_timings,
    )
    print("Report generation complete.")


if __name__ == "__main__":
    main()
