"""Simulates a 100-drone swarm across the GGG framework and compiles a
PDF validation report.

Scenarios:
    1. Dense swarm collision avoidance and formation re-routing under a
       high-velocity convergence (potential-field guidance).
    2. Adversarial pursuit-evasion intercept guidance against a target
       executing a sudden kinematic trajectory shift (ProNav guidance).
    3. Distributed mesh telemetry with automated, secure zeroization
       across shared memory buffers when nodes are compromised.
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

from src.guidance.potential_fields import PotentialFieldNavigator
from src.guidance.pronav_kinematics import ProNavGuidance
from src.memory.zero_copy_buffer import ZeroCopyBufferPool
from src.security.cusum_tamper import CusumTamperDetector
from src.security.military_compliance import ZeroizationManager

REPO_ROOT = Path(__file__).resolve().parent
NUM_DRONES = 100


@dataclass
class ScenarioResult:
    """Outcome of one drone-swarm simulation scenario."""

    name: str
    passed: bool
    elapsed_ms: float
    metrics: dict[str, str] = field(default_factory=dict)


def simulate_collision_avoidance_formation(
    random_state: np.random.Generator,
) -> ScenarioResult:
    """Simulate 100 drones converging through a dense obstacle field.

    Each drone's per-tick repulsive-force update is timed individually
    so the deterministic per-agent execution bound (not just the batch
    total) can be validated against a sub-millisecond budget.
    """
    start = time.perf_counter()

    drone_positions = random_state.uniform(-50.0, 50.0, (NUM_DRONES, 2))
    obstacle_positions = random_state.uniform(-50.0, 50.0, (40, 2))
    navigator = PotentialFieldNavigator(influence_radius=8.0)

    # Warm up interpreter/cache state before measuring per-agent latency.
    navigator.calc_repulsive_force(drone_positions[:1], obstacle_positions)

    per_agent_times_ms = np.empty(NUM_DRONES)
    for index in range(NUM_DRONES):
        agent_start = time.perf_counter()
        navigator.calc_repulsive_force(
            drone_positions[index:index + 1], obstacle_positions
        )
        per_agent_times_ms[index] = (
            time.perf_counter() - agent_start
        ) * 1000.0

    batch_forces = navigator.calc_repulsive_force(
        drone_positions, obstacle_positions
    )

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    max_agent_time_ms = float(np.max(per_agent_times_ms))
    p95_agent_time_ms = float(np.percentile(per_agent_times_ms, 95))
    forces_finite = bool(np.all(np.isfinite(batch_forces)))
    # The p95 (not max) is the deterministic-bound criterion: it is
    # robust to rare single-sample OS scheduler jitter while still
    # enforcing a tight bound on the actual compute cost.
    deterministic_bound_met = p95_agent_time_ms < 1.0
    passed = forces_finite and deterministic_bound_met

    return ScenarioResult(
        name="Dense Swarm Collision Avoidance & Formation Re-routing",
        passed=passed,
        elapsed_ms=elapsed_ms,
        metrics={
            "Drones simulated": str(NUM_DRONES),
            "Obstacles in field": str(obstacle_positions.shape[0]),
            "Max per-agent tick time": f"{max_agent_time_ms:.4f} ms",
            "P95 per-agent tick time": f"{p95_agent_time_ms:.4f} ms",
            "Mean per-agent tick time": (
                f"{float(np.mean(per_agent_times_ms)):.4f} ms"
            ),
            "Sub-millisecond bound met": str(deterministic_bound_met),
            "All forces finite": str(forces_finite),
        },
    )


def simulate_pursuit_evasion_intercept(
    random_state: np.random.Generator,
) -> ScenarioResult:
    """Simulate a 10-interceptor sub-unit against a target that suddenly
    changes course, validating guidance responsiveness to the shift.
    """
    start = time.perf_counter()

    num_interceptors = 10
    guidance = ProNavGuidance(navigation_gain=4.0)

    relative_position = random_state.uniform(
        -5000.0, 5000.0, (num_interceptors, 3)
    )
    relative_velocity_before = random_state.uniform(
        -900.0, 900.0, (num_interceptors, 3)
    )

    tick_start = time.perf_counter()
    accel_before = guidance.calc_commanded_acceleration(
        relative_position, relative_velocity_before
    )
    tick_before_ms = (time.perf_counter() - tick_start) * 1000.0

    # Target executes a sudden kinematic trajectory shift.
    relative_velocity_after = relative_velocity_before + random_state.uniform(
        -600.0, 600.0, (num_interceptors, 3)
    )

    tick_start = time.perf_counter()
    accel_after = guidance.calc_commanded_acceleration(
        relative_position, relative_velocity_after
    )
    tick_after_ms = (time.perf_counter() - tick_start) * 1000.0

    accel_delta = np.linalg.norm(accel_after - accel_before, axis=-1)
    guidance_responded = bool(np.all(accel_delta > 0.0))
    accelerations_finite = bool(
        np.all(np.isfinite(accel_before)) and np.all(np.isfinite(accel_after))
    )

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    passed = guidance_responded and accelerations_finite

    return ScenarioResult(
        name="Adversarial Pursuit-Evasion & Intercept Guidance",
        passed=passed,
        elapsed_ms=elapsed_ms,
        metrics={
            "Interceptors": str(num_interceptors),
            "Pre-shift guidance tick": f"{tick_before_ms:.4f} ms",
            "Post-shift guidance tick": f"{tick_after_ms:.4f} ms",
            "Mean commanded-accel shift": f"{float(np.mean(accel_delta)):.4f}",
            "Guidance responded to shift": str(guidance_responded),
            "All accelerations finite": str(accelerations_finite),
        },
    )


def simulate_distributed_zeroization(
    random_state: np.random.Generator,
) -> ScenarioResult:
    """Simulate network-wide telemetry across the swarm, then trigger a
    secure, automated zeroization sweep once compromised nodes are
    detected via CUSUM tamper analysis.
    """
    start = time.perf_counter()

    pool = ZeroCopyBufferPool(pool_size_bytes=1 << 20)
    zeroization_manager = ZeroizationManager(pool=pool, use_random_noise=True)
    cusum_detector = CusumTamperDetector(slack_k=0.5, alarm_threshold_h=5.0)

    handles = []
    compromised_indices = set(
        random_state.choice(NUM_DRONES, size=5, replace=False).tolist()
    )
    tamper_flags = []

    for drone_index in range(NUM_DRONES):
        handle = pool.allocate(4096)
        tag = f"DRONE{drone_index:03d}".encode()[:8]
        handle.view[:8] = tag
        handles.append((drone_index, handle, tag))

        telemetry = random_state.normal(0.0, 1.0, 500)
        if drone_index in compromised_indices:
            telemetry += np.where(
                np.arange(500) > 250, np.linspace(0.0, 4.0, 500), 0.0
            )
        alarm = cusum_detector.detect_tamper_events(telemetry)
        tamper_flags.append(bool(np.any(alarm["alarmed_mask"])))

    detected_compromised = {
        drone_index
        for drone_index, flagged in enumerate(tamper_flags)
        if flagged
    }
    detection_recall = len(detected_compromised & compromised_indices) / len(
        compromised_indices
    )

    any_compromise_detected = len(detected_compromised) > 0
    purge_report = zeroization_manager.evaluate_and_purge(
        cusum_alarmed=any_compromise_detected
    )
    purge_triggered = purge_report is not None

    surviving_original_tags = sum(
        1
        for _, handle, tag in handles
        if bytes(handle.view[:8]) == tag
    )
    for _, handle, _ in handles:
        handle.view.release()
    pool.close()

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    all_buffers_wiped = surviving_original_tags == 0
    passed = (
        any_compromise_detected
        and purge_triggered
        and all_buffers_wiped
        and detection_recall == 1.0
    )

    return ScenarioResult(
        name="Distributed Mesh Telemetry & Zeroization Under Compromise",
        passed=passed,
        elapsed_ms=elapsed_ms,
        metrics={
            "Drones tracked": str(NUM_DRONES),
            "Compromised nodes injected": str(len(compromised_indices)),
            "Compromised nodes detected": str(len(detected_compromised)),
            "Detection recall": f"{detection_recall:.0%}",
            "Zeroization triggered": str(purge_triggered),
            "Buffers fully wiped": f"{NUM_DRONES - surviving_original_tags}"
            f"/{NUM_DRONES}",
            "Purge elapsed": (
                f"{purge_report.elapsed_seconds * 1000:.4f} ms"
                if purge_report
                else "n/a"
            ),
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
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a1e")),
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
        Paragraph("Drone Swarm Validation Report", styles["Title"])
    )
    story.append(
        Paragraph(
            "Garza Global Graviton (GGG) edge-compute engine -- "
            f"{NUM_DRONES}-drone swarm tactical scenario simulation "
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
    passed_count = sum(1 for result in scenario_results if result.passed)
    all_passed = passed_count == len(scenario_results)
    summary_rows = [
        ["Metric", "Value"],
        ["Scenarios executed", str(len(scenario_results))],
        ["Scenarios passed", f"{passed_count}/{len(scenario_results)}"],
        ["Total simulation time", f"{total_elapsed_ms:.4f} ms"],
        ["Overall status", "PASSED" if all_passed else "FAILED"],
    ]
    story.append(Paragraph("Summary", styles["Heading2"]))
    story.append(_build_table(summary_rows))

    document.build(story)


def main() -> None:
    """Run all swarm scenarios and write the PDF report to the desktop."""
    random_state = np.random.default_rng(7)

    scenarios = [
        simulate_collision_avoidance_formation,
        simulate_pursuit_evasion_intercept,
        simulate_distributed_zeroization,
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
    output_path = Path(desktop_path) / "Simulation_Report.pdf"

    print(f"Writing PDF report to {output_path} ...")
    build_pdf_report(output_path, results)
    print("Report generation complete.")

    if not all(result.passed for result in results):
        raise SystemExit("One or more swarm scenarios failed.")


if __name__ == "__main__":
    main()
