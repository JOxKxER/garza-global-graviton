"""Simulates EW/DDIL tactical scenarios across the GGG framework and
compiles a PDF validation report.

Scenarios:
    1. Dynamic mesh rerouting under active jamming (graph Laplacian +
       fluid congestion routing).
    2. Byzantine node isolation and data-poisoning response (CUSUM
       tamper detection + Byzantine consensus + emergency zeroization).
    3. Non-Markovian spectrum analysis under interference (Mori-Zwanzig
       memory-kernel deconvolution).
"""

from __future__ import annotations

import os
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

from src.distributed.byzantine_consensus import ByzantineConsensusEvaluator
from src.fluid_routing import FluidRoutingEngine
from src.memory.zero_copy_buffer import ZeroCopyBufferPool
from src.physics.mori_zwanzig_kernel import MoriZwanzigKernelEstimator
from src.routing.graph_laplacian import GraphLaplacianAnalyzer
from src.security.cusum_tamper import CusumTamperDetector
from src.security.military_compliance import ZeroizationManager

REPO_ROOT = Path(__file__).resolve().parent


@dataclass
class ScenarioResult:
    """Outcome of one EW/DDIL simulation scenario."""

    name: str
    passed: bool
    elapsed_ms: float
    metrics: dict[str, str] = field(default_factory=dict)


def simulate_mesh_rerouting_under_jamming(
    random_state: np.random.Generator,
) -> ScenarioResult:
    """Simulate high-rate packet loss and validate mesh self-repair.

    Builds a ring-plus-shortcuts mesh, computes its baseline algebraic
    connectivity, then drops a large fraction of links to simulate
    active jamming and re-evaluates partition risk. A fluid congestion
    field derived from the per-node link-loss rate is then used to
    compute reroute vectors that steer traffic away from the jammed
    region without any cloud round-trip.
    """
    start = time.perf_counter()

    num_nodes = 60
    adjacency = np.zeros((num_nodes, num_nodes))
    for node in range(num_nodes):
        adjacency[node, (node + 1) % num_nodes] = 1.0
        adjacency[(node + 1) % num_nodes, node] = 1.0
    shortcut_pairs = random_state.integers(0, num_nodes, size=(40, 2))
    for node_a, node_b in shortcut_pairs:
        if node_a != node_b:
            adjacency[node_a, node_b] = 1.0
            adjacency[node_b, node_a] = 1.0

    laplacian_analyzer = GraphLaplacianAnalyzer()
    baseline = laplacian_analyzer.assess_partition_risk(adjacency)

    jam_mask = random_state.uniform(size=adjacency.shape) < 0.55
    jammed_adjacency = adjacency.copy()
    jammed_adjacency[jam_mask] = 0.0
    jammed_adjacency = np.triu(jammed_adjacency, 1)
    jammed_adjacency += jammed_adjacency.T
    degraded = laplacian_analyzer.assess_partition_risk(jammed_adjacency)

    lost_links = np.sum(adjacency, axis=1) - np.sum(jammed_adjacency, axis=1)
    original_links = np.sum(adjacency, axis=1)
    safe_links = np.where(original_links == 0, 1.0, original_links)
    congestion_1d = np.clip(lost_links / safe_links, 0.0, 1.0)
    grid_size = int(np.ceil(np.sqrt(num_nodes)))
    congestion_field = np.zeros((grid_size, grid_size))
    congestion_field.flat[:num_nodes] = congestion_1d

    fluid_engine = FluidRoutingEngine()
    reroute_x, reroute_y = fluid_engine.compute_reroute_vectors(
        congestion_field
    )
    reroute_magnitude = np.sqrt(reroute_x ** 2 + reroute_y ** 2)

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    connectivity_degraded = (
        degraded["fiedler_value"] < baseline["fiedler_value"]
    )
    rerouting_active = bool(np.all(np.isfinite(reroute_magnitude)))
    passed = connectivity_degraded and rerouting_active

    return ScenarioResult(
        name="Dynamic Mesh Rerouting Under Jamming",
        passed=passed,
        elapsed_ms=elapsed_ms,
        metrics={
            "Baseline Fiedler value": f"{baseline['fiedler_value']:.4f}",
            "Jammed Fiedler value": f"{degraded['fiedler_value']:.4f}",
            "Jammed partition risk flagged": str(degraded["partition_risk"]),
            "Links dropped": f"{int(np.sum(jam_mask) / 2)}",
            "Mean reroute vector magnitude": (
                f"{np.mean(reroute_magnitude):.4f}"
            ),
        },
    )


def simulate_byzantine_isolation_and_zeroize(
    random_state: np.random.Generator,
) -> ScenarioResult:
    """Simulate a poisoned node, detect it, and trigger emergency purge.

    Injects a slow drift-style data-poisoning attack into one node's
    telemetry stream, confirms CUSUM flags the drift, confirms the
    swarm's Byzantine fault tolerance still holds with that one node
    isolated (but fails once too many nodes are compromised), then
    fires an automated zeroization purge against the compromised node's
    memory pool.
    """
    start = time.perf_counter()

    baseline = random_state.normal(0.0, 1.0, 5000)
    drift = np.linspace(0.0, 4.0, 5000)
    poisoned_signal = baseline + np.where(
        np.arange(5000) > 2500, drift, 0.0
    )

    cusum_detector = CusumTamperDetector(slack_k=0.5, alarm_threshold_h=5.0)
    tamper_result = cusum_detector.detect_tamper_events(poisoned_signal)
    tamper_detected = bool(np.any(tamper_result["alarmed_mask"]))

    bft_evaluator = ByzantineConsensusEvaluator()
    total_nodes = 13
    consensus_single_fault = bool(
        bft_evaluator.is_consensus_viable(total_nodes, 1)
    )
    consensus_multi_fault = bool(
        bft_evaluator.is_consensus_viable(total_nodes, 5)
    )

    pool = ZeroCopyBufferPool(pool_size_bytes=1 << 16)
    zeroization_manager = ZeroizationManager(pool=pool, use_random_noise=True)
    handle = pool.allocate(256)
    handle.view[:16] = b"POISONED-TELEM01"

    purge_report = zeroization_manager.evaluate_and_purge(
        cusum_alarmed=tamper_detected
    )
    purge_triggered = purge_report is not None
    data_destroyed = bytes(handle.view[:16]) != b"POISONED-TELEM01"
    handle.view.release()
    pool.close()

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    passed = (
        tamper_detected
        and consensus_single_fault
        and not consensus_multi_fault
        and purge_triggered
        and data_destroyed
    )

    return ScenarioResult(
        name="Byzantine Node Isolation & Data Poisoning Response",
        passed=passed,
        elapsed_ms=elapsed_ms,
        metrics={
            "CUSUM tamper detected": str(tamper_detected),
            "First alarm index": str(tamper_result["first_alarm_index"]),
            "Consensus viable (1 faulty/13)": str(consensus_single_fault),
            "Consensus viable (5 faulty/13)": str(consensus_multi_fault),
            "Zeroization triggered": str(purge_triggered),
            "Poisoned data destroyed": str(data_destroyed),
            "Purge elapsed": (
                f"{purge_report.elapsed_seconds * 1000:.4f} ms"
                if purge_report
                else "n/a"
            ),
        },
    )


def simulate_non_markovian_spectrum_analysis(
    random_state: np.random.Generator,
) -> ScenarioResult:
    """Deconvolve a memory kernel from interference-degraded telemetry.

    Builds a clean autocorrelation/kernel pair, derives the true
    derivative signal, then corrupts the observed derivative with
    interference noise before deconvolving. Success is judged by how
    closely the noisy-derived kernel, once re-applied, reconstructs the
    original clean tactical signal despite the interference.
    """
    start = time.perf_counter()

    time_step = 0.05
    num_samples = 200
    time_axis = np.arange(num_samples) * time_step
    autocorrelation = np.exp(-time_axis / 1.5)
    true_kernel = 4.0 * np.exp(-time_axis / 0.4)

    estimator = MoriZwanzigKernelEstimator(time_step=time_step)
    clean_derivative = estimator.convolve_kernel(true_kernel, autocorrelation)

    interference = random_state.normal(
        0.0, 0.02 * np.max(np.abs(clean_derivative)), num_samples
    )
    noisy_derivative = clean_derivative + interference

    estimated_kernel = estimator.estimate_kernel(
        autocorrelation, noisy_derivative
    )
    reconstructed_derivative = estimator.convolve_kernel(
        estimated_kernel, autocorrelation
    )

    signal_scale = np.sqrt(np.mean(clean_derivative ** 2))
    reconstruction_error = np.sqrt(
        np.mean((reconstructed_derivative - clean_derivative) ** 2)
    )
    relative_error = reconstruction_error / signal_scale

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    passed = bool(relative_error < 0.10)

    return ScenarioResult(
        name="Non-Markovian Spectrum Analysis Under Interference",
        passed=passed,
        elapsed_ms=elapsed_ms,
        metrics={
            "Samples": str(num_samples),
            "Interference std (rel. to signal)": "2.0%",
            "Relative reconstruction RMS error": f"{relative_error:.4%}",
            "Pass threshold": "< 10.00%",
        },
    )


def _build_table(
    rows: list[list[str]], col_widths: list[float] | None = None
) -> Table:
    """Build a consistently styled reportlab Table from a list of rows."""
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#5f1e1e")),
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


def build_pdf_report(
    output_path: Path, scenario_results: list[ScenarioResult]
) -> None:
    """Render every scenario's metrics into a formatted PDF at output_path."""
    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )
    story = []

    story.append(
        Paragraph(
            "EW Resilience &amp; Tactical Mesh Validation Report",
            styles["Title"],
        )
    )
    story.append(
        Paragraph(
            "Garza Global Graviton (GGG) edge-compute engine -- "
            "Electronic Warfare (EW) and DDIL scenario simulation "
            "results.",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.25 * inch))

    for index, result in enumerate(scenario_results, start=1):
        story.append(
            Paragraph(f"{index}. {result.name}", styles["Heading2"])
        )
        rows = [["Metric", "Value"]]
        rows.extend([[key, value] for key, value in result.metrics.items()])
        rows.append(["Execution time", f"{result.elapsed_ms:.4f} ms"])
        rows.append(["Status", "PASSED" if result.passed else "FAILED"])
        story.append(_build_table(rows))
        story.append(Spacer(1, 0.25 * inch))

    total_elapsed_ms = sum(result.elapsed_ms for result in scenario_results)
    all_passed = all(result.passed for result in scenario_results)
    summary_rows = [
        ["Metric", "Value"],
        ["Scenarios executed", str(len(scenario_results))],
        [
            "Scenarios passed",
            f"{sum(1 for r in scenario_results if r.passed)}"
            f"/{len(scenario_results)}",
        ],
        ["Total simulation time", f"{total_elapsed_ms:.4f} ms"],
        ["Overall status", "PASSED" if all_passed else "FAILED"],
    ]
    story.append(Paragraph("Summary", styles["Heading2"]))
    story.append(_build_table(summary_rows))

    document.build(story)


def main() -> None:
    """Run all EW/DDIL scenarios and write the PDF report to the desktop."""
    random_state = np.random.default_rng(42)

    scenarios = [
        simulate_mesh_rerouting_under_jamming,
        simulate_byzantine_isolation_and_zeroize,
        simulate_non_markovian_spectrum_analysis,
    ]

    results: list[ScenarioResult] = []
    for scenario in scenarios:
        print(f"Running: {scenario.__name__} ...")
        result = scenario(random_state)
        status = "PASSED" if result.passed else "FAILED"
        print(f"  {status} in {result.elapsed_ms:.4f} ms")
        results.append(result)

    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    os.makedirs(desktop_path, exist_ok=True)
    output_path = Path(desktop_path) / "EW_Resilience_Simulation_Report.pdf"

    print(f"Writing PDF report to {output_path} ...")
    build_pdf_report(output_path, results)
    print("Report generation complete.")

    if not all(result.passed for result in results):
        raise SystemExit("One or more EW/DDIL scenarios failed.")


if __name__ == "__main__":
    main()
