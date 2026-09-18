"""TradeAssist signal analyzer.

Evaluates candidate positions against a dynamic, equity-tiered risk
threshold defined by ``get_dynamic_threshold()``. ``config.config`` is
still imported for any legacy static keys other modules may read.
"""

from config import config  # noqa: F401  (kept for legacy keys)

# --- Dynamic threshold tier boundaries ---
_BASE_EQUITY = 100.0          # tier 1 starts here at 90%
_BASE_THRESHOLD = 0.90
_TIER_STEP_EQUITY = 100.0     # each $100 of growth drops the threshold
_TIER_STEP_PCT = 0.05         # ...by 5%
_TIER_CAP_EQUITY = 1000.0     # tiers stop here
_CAP_THRESHOLD = 0.10         # threshold at the $1,000 tier
_FLOOR_THRESHOLD = 0.05       # never risk-check below 5%
_TAPER_RANGE = 4000.0         # $1,000 -> $5,000 smooth 10% -> 5% taper


def get_dynamic_threshold(equity: float) -> float:
    """Return the maximum position-size fraction allowed for ``equity``.

    Schedule:
      * $100 equity      -> 90% (aggressive starter tier)
      * each +$100 above -> drops 5% per step until $1,000 (10%)
      * $1,000+          -> smooth taper from 10% down to a 5% floor,
                            static at 5% beyond the taper range.
    """
    equity = max(0.0, float(equity))

    if equity < _TIER_CAP_EQUITY:
        steps = int((equity - _BASE_EQUITY) // _TIER_STEP_EQUITY)
        threshold = _BASE_THRESHOLD - steps * _TIER_STEP_PCT
        return max(_FLOOR_THRESHOLD, min(_BASE_THRESHOLD, threshold))

    # $1,000 and above: linear taper from 10% toward the 5% floor.
    progress = min(1.0, (equity - _TIER_CAP_EQUITY) / _TAPER_RANGE)
    return _CAP_THRESHOLD - progress * (_CAP_THRESHOLD - _FLOOR_THRESHOLD)


def check_position_size(position_fraction: float, equity: float | None = None) -> dict:
    """Assess a proposed position size against the dynamic threshold.

    ``position_fraction`` is the fraction of account equity the position
    would occupy (e.g. 0.03 == 3%). ``equity`` is the current total account
    value; when omitted the starter tier ($100) is assumed.
    """
    if equity is None:
        equity = _BASE_EQUITY
    threshold = get_dynamic_threshold(equity)
    oversized = position_fraction > threshold
    return {
        "position_fraction": position_fraction,
        "threshold": threshold,
        "equity": equity,
        "oversized": oversized,
        "recommendation": "reject" if oversized else "accept",
    }
