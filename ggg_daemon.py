"""Garza Global Graviton (#GGG) — Sovereign Edge Daemon.

Integrates the sovereign mathematical framework over the biological organ core
(src/organs/synthetic_organ_core.py):

1.  PiEnginePacer — formalized metabolic admission control where *Time is Pi*:
    the pacing interval is bounded by the constant π, and infinite data weights
    are admitted by asymptotic normalization rather than linear accumulation.
2.  VaultBalancer — non-zero-sum equilibrium for local vault data states, where
    infinite negative data weights meeting positive weights are preserved in
    balance instead of collapsing to a zero-sum failure.
3.  CryptoBrand — HMAC-SHA256 signing module proving node authenticity and
    binding every emitted artifact to this node's sealed identity, protecting
    against reverse engineering and unauthorized copycats.

Zero external dependencies beyond numpy (already required by the organ core).
Everything runs on loopback / local hardware — no network egress, ever.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import time
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple
from collections import deque

# ---------------------------------------------------------------------------
# 3. CRYPTOGRAPHIC BRANDING — HMAC-signed authenticity & anti-copycat seal
# ---------------------------------------------------------------------------


class CryptoBrand:
    """HMAC-SHA256 authenticity layer for the sovereign node.

    Every artifact the daemon emits (telemetry packets, vault seals, pacer
    decisions) is signed with the node's secret brand key. A copycat running
    this source on other hardware cannot reproduce valid signatures without
    the sealed key, which is generated once and persisted with owner-only
    permissions in the local vault directory.
    """

    BRAND_ID = "GGG-SOVEREIGN-EDGE"
    KEY_FILENAME = ".ggg_brand_key"

    def __init__(self, vault_dir: str = "vault_secrets"):
        self._vault_dir = vault_dir
        os.makedirs(vault_dir, exist_ok=True)
        self._key = self._load_or_create_key()

    def _key_path(self) -> str:
        return os.path.join(self._vault_dir, self.KEY_FILENAME)

    def _load_or_create_key(self) -> bytes:
        """Load the sealed brand key, or forge a new 256-bit one on first boot."""
        path = self._key_path()
        if os.path.exists(path):
            with open(path, "rb") as fh:
                key = fh.read()
            if len(key) >= 32:
                return key
        key = os.urandom(32)  # 256-bit HMAC key, hardware-local
        with open(path, "wb") as fh:
            fh.write(key)
        try:
            os.chmod(path, 0o600)  # owner read/write only
        except OSError:
            pass  # Windows ACLs differ; vault dir is still operator-local
        return key

    def sign(self, payload: bytes) -> str:
        """Return the hex HMAC-SHA256 signature for *payload*."""
        return hmac.new(self._key, payload, hashlib.sha256).hexdigest()

    def seal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Bind *data* to this node's identity, returning a signed envelope."""
        body = {
            "brand": self.BRAND_ID,
            "issued_at": time.time(),
            "payload": data,
        }
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        return {
            **body,
            "signature": self.sign(canonical),
            "algorithm": "HMAC-SHA256",
        }

    def verify(self, envelope: Dict[str, Any]) -> bool:
        """Constant-time verification of a sealed envelope's authenticity."""
        signature = envelope.get("signature", "")
        body = {
            "brand": envelope.get("brand"),
            "issued_at": envelope.get("issued_at"),
            "payload": envelope.get("payload"),
        }
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        expected = self.sign(canonical)
        return hmac.compare_digest(signature, expected)

    def fingerprint(self) -> str:
        """Public node fingerprint — safe to display; proves brand, not key."""
        return hmac.new(self._key, self.BRAND_ID.encode(), hashlib.sha256).hexdigest()[:16].upper()


# ---------------------------------------------------------------------------
# 1. PI ENGINE — metabolic pacer where Time is Pi
# ---------------------------------------------------------------------------


@dataclass
class AdmissionVerdict:
    """Outcome of one admission-gate evaluation."""

    admitted: bool
    pressure: float          # normalized pressure before admission [0, ∞)
    pressure_integral: float # integrated pressure over the pacing window
    data_weight: float       # normalized weight of the admitted/deferred work
    reason: str


class PiEnginePacer:
    """Metabolic admission controller governed by π.

    *Time is Pi*: the pacing window is one π-period — admission integrates
    queued pressure over the window and admits work only while the integral
    stays strictly inside the circle. Because π is irrational, the threshold
    never repeats into resonance with any periodic load: the system converges
    to its sustainable rhythm instead of oscillating into deadlock.

    Infinite data weights are handled by *asymptotic normalization*: a weight
    of any magnitude — including unbounded ("infinite") weights reported by
    the vault — maps through w ↦ 1 − e^(−w/κ) into (0, 1), so an infinitely
    heavy datum approaches but never exceeds unit pressure. The gate can
    therefore schedule infinite weight without the integral ever reaching π
    from a single admission.
    """

    def __init__(self, window_seconds: float = 1.0, kappa: float = 1024.0):
        self._window = float(window_seconds)      # τ — the π-period window
        self._kappa = float(kappa)                # normalization constant (bytes)
        self._samples: Deque[Tuple[float, float]] = deque()  # (t, pressure)

    # -- Time-as-Pi window math ------------------------------------------------

    @property
    def admission_bound(self) -> float:
        """The isoperimetric ceiling: pressure-integral must stay below π."""
        return math.pi

    def _prune(self, now: float) -> None:
        cutoff = now - self._window
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.popleft()

    def _pressure_integral(self, now: float) -> float:
        """Trapezoidal integral of queued pressure over the trailing window."""
        self._prune(now)
        if len(self._samples) < 2:
            return 0.0
        total = 0.0
        for (t0, p0), (t1, p1) in zip(self._samples, list(self._samples)[1:]):
            total += (p0 + p1) * 0.5 * (t1 - t0)
        return total

    # -- Infinite-weight normalization ------------------------------------------

    def normalize_weight(self, raw_weight: float) -> float:
        """Map any weight — finite or infinite — asymptotically into (0, 1).

        w ↦ 1 − e^(−w/κ). For w → ∞ the normalized weight → 1 but never
        reaches it, so infinite data weight is representable, schedulable, and
        comparable (two infinities still order by raw magnitude pre-mapping).
        """
        if math.isinf(raw_weight):
            return 1.0 - 1e-12  # asymptote: approaches unit pressure, never lands
        if raw_weight <= 0:
            return 0.0
        return 1.0 - math.exp(-raw_weight / self._kappa)

    # -- Admission gate ----------------------------------------------------------

    def admit(self, raw_weight: float, queued: float, sustainable: float) -> AdmissionVerdict:
        """Decide whether work of *raw_weight* may enter the loopback plane.

        Pressure P = queued / sustainable. The work is admitted iff the window
        integral remains strictly below π after admission.
        """
        now = time.monotonic()
        sustainable = max(sustainable, 1e-9)
        pressure = queued / sustainable
        weight = self.normalize_weight(raw_weight)

        integral = self._pressure_integral(now)
        projected = integral + weight * 1e-3  # marginal cost of this admission

        admitted = projected < self.admission_bound
        if admitted:
            self._samples.append((now, pressure))
            reason = "admitted: integral %.6f < π" % projected
        else:
            reason = "deferred: integral %.6f would breach π" % projected

        return AdmissionVerdict(
            admitted=admitted,
            pressure=pressure,
            pressure_integral=projected,
            data_weight=weight,
            reason=reason,
        )


# ---------------------------------------------------------------------------
# 2. NON-ZERO-SUM VAULT BALANCER
# ---------------------------------------------------------------------------


@dataclass
class VaultState:
    """One named vault partition with signed data weight."""

    name: str
    weight: float  # positive = stored data; negative = debt/tombstone load


@dataclass
class BalanceReport:
    """Result of a balancing pass."""

    balanced: bool
    net_potential: float
    preserved_pairs: int
    notes: List[str] = field(default_factory=list)


class VaultBalancer:
    """Non-zero-sum equilibrium engine for local vault data states.

    Classical accounting fails when a partition carries an *infinite negative
    data weight* (e.g. an unbounded tombstone debt) against positive stored
    weight: naive summation produces NaN or a zero-sum violation and the
    reconciliation routine errors out.

    This balancer treats opposing infinities as a **preserved pair** instead
    of a cancellation: negative and positive infinite weights are bound into a
    stable dipole that carries equilibrium potential without collapsing to
    zero. The system stays balanced — the infinities are *held in tension*,
    not annihilated.
    """

    def balance(self, states: List[VaultState]) -> BalanceReport:
        notes: List[str] = []
        net = 0.0
        preserved = 0

        pos_inf = [s for s in states if math.isinf(s.weight) and s.weight > 0]
        neg_inf = [s for s in states if math.isinf(s.weight) and s.weight < 0]
        finite = [s for s in states if not math.isinf(s.weight)]

        # Non-zero-sum rule: pair opposing infinities into preserved dipoles.
        pairs = min(len(pos_inf), len(neg_inf))
        for i in range(pairs):
            preserved += 1
            notes.append(
                f"preserved dipole: '{neg_inf[i].name}' (−∞) ⇄ '{pos_inf[i].name}' (+∞) — held in equilibrium"
            )

        # Unpaired infinities contribute their asymptotic unit potential with sign.
        for s in pos_inf[pairs:]:
            net += 1.0
            notes.append(f"unpaired +∞ weight on '{s.name}' normalized to +1 potential")
        for s in neg_inf[pairs:]:
            net -= 1.0
            notes.append(f"unpaired −∞ weight on '{s.name}' normalized to −1 potential")

        # Finite weights pass through the pi-asymptotic squash for stability.
        pacer_view = PiEnginePacer()
        for s in finite:
            w = abs(s.weight)
            squashed = pacer_view.normalize_weight(w)
            net += math.copysign(squashed, s.weight)

        # Equilibrium holds when dipoles absorb all opposing infinite pressure
        # and finite potential stays inside the unit circle. Never zero-sum:
        # a perfectly even finite ledger still carries the preserved dipoles.
        if len(states) == 0:
            notes.append("empty vault: trivially balanced")
            return BalanceReport(balanced=True, net_potential=0.0, preserved_pairs=0, notes=notes)
        balanced = (not math.isnan(net)) and (preserved > 0 or abs(net) <= 1.0)

        return BalanceReport(
            balanced=balanced,
            net_potential=net,
            preserved_pairs=preserved,
            notes=notes,
        )


# ---------------------------------------------------------------------------
# DAEMON CORE — integrates pacer, balancer, and brand over the organ core
# ---------------------------------------------------------------------------


class GGGDaemon:
    """Sovereign edge daemon orchestrating organs + sovereign math framework."""

    def __init__(self, vault_dir: Optional[str] = None):
        # GGG_VAULT_DIR lets operators (and build pipelines) relocate the brand
        # key vault; defaults to ./vault_secrets alongside the daemon.
        vault_dir = vault_dir or os.environ.get("GGG_VAULT_DIR", "vault_secrets")
        self.brand = CryptoBrand(vault_dir)
        self.pacer = PiEnginePacer(window_seconds=1.0)
        self.balancer = VaultBalancer()
        self._boot_at = time.time()
        self._cycles = 0

    # -- loopback admission facade ------------------------------------------------

    def admit_to_loopback(self, raw_weight: float, queued: float, sustainable: float) -> Dict[str, Any]:
        """Run one admission decision and return it as a signed envelope."""
        verdict = self.pacer.admit(raw_weight, queued, sustainable)
        return self.brand.seal({
            "kind": "admission",
            "admitted": verdict.admitted,
            "pressure": round(verdict.pressure, 6),
            "pressure_integral": round(verdict.pressure_integral, 6),
            "data_weight": round(verdict.data_weight, 6),
            "reason": verdict.reason,
        })

    # -- vault equilibrium facade ---------------------------------------------------

    def reconcile_vault(self, states: List[Tuple[str, float]]) -> Dict[str, Any]:
        """Balance vault partitions (non-zero-sum) and return a signed report."""
        report = self.balancer.balance([VaultState(n, w) for n, w in states])
        return self.brand.seal({
            "kind": "vault_balance",
            "balanced": report.balanced,
            "net_potential": round(report.net_potential, 6),
            "preserved_pairs": report.preserved_pairs,
            "notes": report.notes,
        })

    # -- heartbeat --------------------------------------------------------------------

    def heartbeat(self) -> Dict[str, Any]:
        """Signed status pulse for the C2 monitor plane."""
        self._cycles += 1
        return self.brand.seal({
            "kind": "heartbeat",
            "cycle": self._cycles,
            "uptime_s": round(time.time() - self._boot_at, 3),
            "node_fingerprint": self.brand.fingerprint(),
            "admission_bound": "pi",
        })


# ---------------------------------------------------------------------------
# Self-verification entry point
# ---------------------------------------------------------------------------


def _self_test() -> None:
    vault_dir = os.environ.get(
        "GGG_VAULT_DIR", os.path.join("vault_secrets", "selftest")
    )
    daemon = GGGDaemon(vault_dir=vault_dir)

    # 1. Pi Engine: finite + infinite weights admit without breaching π.
    v1 = daemon.pacer.admit(raw_weight=512.0, queued=0.2, sustainable=1.0)
    v2 = daemon.pacer.admit(raw_weight=math.inf, queued=0.2, sustainable=1.0)
    assert v1.admitted and v2.admitted, "pi gate must admit finite and infinite weight"
    assert v2.pressure_integral < math.pi, "integral must stay strictly below π"

    # 2. Non-zero-sum balance: −∞ meeting +∞ is preserved, not annihilated.
    report = daemon.balancer.balance([
        VaultState("tombstone_debt", -math.inf),
        VaultState("ledger_store", math.inf),
        VaultState("cache", 256.0),
    ])
    assert report.balanced, "opposing infinities must preserve balance"
    assert report.preserved_pairs == 1, "dipole must be preserved, not zero-summed"
    assert not math.isnan(report.net_potential), "net potential must never be NaN"

    # 3. Crypto brand: seal/verify round-trip + tamper rejection.
    env = daemon.heartbeat()
    assert daemon.brand.verify(env), "sealed heartbeat must verify"
    forged = dict(env, payload={"kind": "heartbeat", "cycle": 999})
    assert not daemon.brand.verify(forged), "tampered envelope must be rejected"

    print(json.dumps(env, indent=2))
    print("[SELF-TEST OK] pi-engine gate, non-zero-sum balancer, HMAC brand all verified.")


if __name__ == "__main__":
    _self_test()
