"""Joker Compiler Bridge: routes math-heavy codegen to vetted GGG modules.

Tactical use: a local LLM asked to write pathfinding, optimization, or
simulation code will often hallucinate a slow or incorrect procedural
implementation. This bridge scans a user's natural-language project
request, detects which categories of heavy computation it implies, and
builds a grounding context listing real import paths and usage hints from
the vectorized 61-module GGG engine in `src/`, steering generated code
toward proven primitives instead of reinvented math.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GgxModuleReference:
    """A single routable GGG module: where it lives and when to use it."""

    import_path: str
    class_name: str
    keywords: tuple[str, ...]
    usage_hint: str


CATEGORY_REGISTRY: dict[str, tuple[GgxModuleReference, ...]] = {
    "pathfinding_routing": (
        GgxModuleReference(
            "src.routing.hungarian_assignment",
            "SensorTargetAssigner",
            ("pathfind", "assign", "matching", "allocation", "routing"),
            "Optimal one-to-one agent/target assignment (Hungarian "
            "algorithm).",
        ),
        GgxModuleReference(
            "src.routing.haversine_geodesic",
            "HaversineGeodesicCalculator",
            ("distance", "geodesic", "gps", "latitude", "longitude"),
            "Vectorized great-circle distance between coordinate pairs.",
        ),
        GgxModuleReference(
            "src.routing.graph_laplacian",
            "GraphLaplacianAnalyzer",
            ("graph", "network", "mesh", "connectivity", "partition"),
            "Algebraic connectivity / mesh partition-risk analysis.",
        ),
    ),
    "guidance_control": (
        GgxModuleReference(
            "src.guidance.pronav_kinematics",
            "ProNavGuidance",
            ("intercept", "guidance", "pursuit", "chase", "missile"),
            "Proportional-navigation intercept acceleration commands.",
        ),
        GgxModuleReference(
            "src.guidance.potential_fields",
            "PotentialFieldNavigator",
            ("avoidance", "obstacle", "collision", "swarm navigation"),
            "Reactive repulsive-force obstacle avoidance for agents.",
        ),
        GgxModuleReference(
            "src.guidance.control_barrier_functions",
            "ControlBarrierFunction",
            ("safety", "constraint", "barrier", "envelope"),
            "Hard safety-envelope gating for proposed control actions.",
        ),
        GgxModuleReference(
            "src.robotics.damped_least_squares",
            "DampedLeastSquaresSolver",
            ("inverse kinematics", "arm", "gimbal", "jacobian"),
            "Singularity-free inverse kinematics for arms/gimbals.",
        ),
    ),
    "optimization_resource_allocation": (
        GgxModuleReference(
            "src.power.kkt_water_filling",
            "WaterFillingAllocator",
            ("allocate", "power", "bandwidth", "resource", "channel"),
            "KKT water-filling optimal power/resource allocation.",
        ),
        GgxModuleReference(
            "src.power.ac_power_arbitrage",
            "AcPowerArbitrageScheduler",
            ("dispatch", "grid", "arbitrage", "energy", "cost"),
            "Merit-order minimum-cost power dispatch across nodes.",
        ),
        GgxModuleReference(
            "src.c2.isaacs_minimax",
            "IsaacsMinimaxSolver",
            ("minimax", "game theory", "pursuit-evasion", "adversarial"),
            "Discretized differential-game minimax safety bounds.",
        ),
    ),
    "simulation_physics": (
        GgxModuleReference(
            "src.swarm.kuramoto_vicsek",
            "KuramotoVicsekModel",
            ("swarm", "flocking", "synchronization", "oscillator"),
            "Coupled-oscillator phase/heading synchronization model.",
        ),
        GgxModuleReference(
            "src.fluid_routing",
            "FluidRoutingEngine",
            ("fluid", "congestion", "flow", "network traffic"),
            "Navier-Stokes-style congestion field simulation.",
        ),
        GgxModuleReference(
            "src.astrodynamics.vis_viva_kinematics",
            "VisVivaSolver",
            ("orbit", "satellite", "orbital velocity", "astrodynamics"),
            "Closed-form orbital velocity from the Vis-Viva equation.",
        ),
    ),
    "estimation_filtering": (
        GgxModuleReference(
            "src.estimation.particle_resampler",
            "ParticleResampler",
            ("particle filter", "tracking", "non-gaussian", "estimation"),
            "Particle-filter weight update and systematic resampling.",
        ),
        GgxModuleReference(
            "src.estimation.chi_squared_gating",
            "ChiSquaredGate",
            ("gating", "outlier", "clutter", "mahalanobis"),
            "Statistical gating to reject outlier/clutter measurements.",
        ),
        GgxModuleReference(
            "src.estimation.covariance_fusion",
            "CovarianceIntersectionFuser",
            ("sensor fusion", "covariance", "fuse", "multi-sensor"),
            "Consistent multi-sensor covariance intersection fusion.",
        ),
    ),
    "security_anomaly_detection": (
        GgxModuleReference(
            "src.security.cusum_tamper",
            "CusumTamperDetector",
            ("drift", "tamper", "anomaly", "cusum", "changepoint"),
            "CUSUM change-point detection for slow sensor drift/tamper.",
        ),
        GgxModuleReference(
            "src.security.ew_circuit_breaker",
            "SpoofingCircuitBreaker",
            ("spoofing", "jamming", "surprise", "circuit breaker"),
            "Shannon-surprise tripwire that quarantines bad telemetry.",
        ),
    ),
    "matrix_linear_algebra": (
        GgxModuleReference(
            "src.holographic_encoder",
            "HolographicEncoder",
            ("compress", "svd", "dimensionality", "matrix"),
            "SVD-based low-rank matrix compression/reconstruction.",
        ),
    ),
}


class JokerCompilerBridge:
    """Detects heavy-compute categories and grounds prompts in GGG modules."""

    def detect_categories(self, user_prompt: str) -> list[str]:
        """Return the GGG categories whose keywords appear in the prompt.

        Tactical advantage: a cheap, fully local keyword scan decides
        whether a project request needs GGG grounding before any tokens
        are spent on generation.
        """
        prompt_lower = user_prompt.lower()
        matched: list[str] = []
        for category, references in CATEGORY_REGISTRY.items():
            for reference in references:
                if any(kw in prompt_lower for kw in reference.keywords):
                    matched.append(category)
                    break
        return matched

    def build_grounding_context(self, user_prompt: str) -> str:
        """Build an LLM-ready context block listing relevant GGG modules.

        Tactical advantage: prepending this block to the user's prompt
        gives the local LLM concrete, correct import paths and usage
        hints for every category its request implies, steering it away
        from hand-rolled, unvectorized, or incorrect math code.
        """
        categories = self.detect_categories(user_prompt)
        if not categories:
            return ""

        lines = [
            "GGG ENGINE MODULES AVAILABLE (use these instead of writing "
            "your own math/optimization/simulation logic):"
        ]
        seen_imports: set[str] = set()
        for category in categories:
            for reference in CATEGORY_REGISTRY[category]:
                if reference.import_path in seen_imports:
                    continue
                seen_imports.add(reference.import_path)
                lines.append(
                    f"- from {reference.import_path} import "
                    f"{reference.class_name}  # {reference.usage_hint}"
                )
        return "\n".join(lines)
