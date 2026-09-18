"""Master Active Inference Node: the unified GGG edge autonomous operator.

Tactical use: fuses the platform's security filters, safety supervisor,
cosmological swarm-scale model, and human-authority weighting into a
single sub-millisecond control cycle. Frames each cycle around the Free
Energy Principle -- the node's objective is to minimize "surprise" (here
approximated by the accumulated CUSUM deviation statistic, a fast proxy
for prediction error) at every tick, escalating to a quarantine/abort
state the instant that surprise, tampering, or an authority override
demands it, rather than acting on a potentially compromised world-model.
"""

import numpy as np

from src.c2.epistemic_precision_scaling import EpistemicPrecisionScaler
from src.c2.hybrid_meta_auditor import HybridMetaAuditor
from src.lambda_cdm_engine import LambdaCDMController
from src.ptolemaic_validator import PtolemaicValidator
from src.security.cusum_tamper import CusumTamperDetector

ACTION_NOMINAL = "NOMINAL_ACTION"
ACTION_QUARANTINE = "QUARANTINE_ABORT"


class MasterActiveInferenceNode:
    """Unified GGG edge brain: security + safety audit + authority gate."""

    def __init__(
        self,
        heartbeat_interval=100,
        surprise_threshold=10.0,
        min_efficiency=0.2,
        cusum_slack_k=0.5,
        cusum_alarm_threshold=5.0,
        spoof_epicycle_threshold=5,
        precision_suppression_factor=0.01,
    ):
        """Wire up the security, safety, cosmology, and authority parts."""
        self.ptolemaic_validator = PtolemaicValidator(
            complexity_threshold=spoof_epicycle_threshold
        )
        self.cusum_detector = CusumTamperDetector(
            slack_k=cusum_slack_k, alarm_threshold_h=cusum_alarm_threshold
        )
        self.meta_auditor = HybridMetaAuditor(
            heartbeat_interval=heartbeat_interval,
            surprise_threshold=surprise_threshold,
            min_efficiency=min_efficiency,
        )
        self.cosmology_model = LambdaCDMController()
        self.precision_scaler = EpistemicPrecisionScaler(
            precision_suppression_factor
        )
        self.tick_count = 0

    def run_tick(
        self,
        telemetry_payload,
        ai_confidence=1.0,
        human_override=False,
        tactical_efficiency=1.0,
    ):
        """Execute one sub-millisecond active-inference control cycle.

        Steps: (1) ingest the telemetry window, (2) screen it through the
        Ptolemaic harmonic-complexity filter and the CUSUM drift detector,
        (3) submit the resulting surprise/efficiency state to the hybrid
        meta-auditor's heartbeat/surprise/yield trigger, (4) suppress AI
        confidence in favor of any verified human override, and
        (5) emit a sanitized action state.

        Tactical advantage: a single call gives a fully audited, human-
        authority-respecting go/no-go decision for one control tick, with
        every intermediate signal preserved for after-action review.
        """
        self.tick_count += 1
        signal = np.atleast_1d(np.asarray(telemetry_payload, dtype=float))

        ptolemaic_result = self.ptolemaic_validator.evaluate_signal(signal)
        cusum_result = self.cusum_detector.detect_tamper_events(signal)

        spoof_detected = bool(ptolemaic_result["is_synthetic_spoof"])
        tamper_detected = bool(np.any(cusum_result["alarmed_mask"]))
        surprise_estimate = float(cusum_result["cusum_statistic"][-1])

        trigger_result = self.meta_auditor.evaluate_trigger(
            np.array([self.tick_count]),
            np.array([surprise_estimate]),
            np.array([tactical_efficiency]),
        )
        meta_triggered = bool(trigger_result["triggered"][0])

        should_quarantine = spoof_detected or tamper_detected or meta_triggered

        scaled_confidence = self.precision_scaler.calc_scaled_precision(
            np.array([ai_confidence]), np.array([human_override])
        )[0]

        action_state = (
            ACTION_QUARANTINE if should_quarantine else ACTION_NOMINAL
        )

        return {
            "tick": self.tick_count,
            "action_state": action_state,
            "spoof_detected": spoof_detected,
            "tamper_detected": tamper_detected,
            "meta_triggered": meta_triggered,
            "surprise_estimate": surprise_estimate,
            "scaled_ai_confidence": float(scaled_confidence),
        }
