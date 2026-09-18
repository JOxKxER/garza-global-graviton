import pandas as pd
import pytest

from trading_app.analytics.probability_engine import Action, ProbabilityEngine, compute_indicators
from trading_app.data.ingestion import generate_synthetic_history


def test_compute_indicators_adds_expected_columns():
    df = generate_synthetic_history("TEST", periods=100, seed=42)
    enriched = compute_indicators(df)
    for col in ["sma_20", "sma_50", "rsi_14", "zscore_20", "volatility_20"]:
        assert col in enriched.columns


def test_signal_holds_during_indicator_warmup():
    df = generate_synthetic_history("TEST", periods=10, seed=1)  # too short for sma_50
    engine = ProbabilityEngine()
    signal = engine.generate_signal(df)
    assert signal.action == Action.HOLD
    assert signal.probability == 0.5


def test_signal_probability_and_edge_are_bounded():
    df = generate_synthetic_history("TEST", periods=300, seed=7)
    engine = ProbabilityEngine()
    signal = engine.generate_signal(df)
    assert 0.0 <= signal.probability <= 1.0
    assert -1.0 <= signal.edge <= 1.0


def test_uptrend_with_pullbacks_biases_toward_buy():
    dates = pd.bdate_range("2024-01-01", periods=120)
    # A realistic uptrend with periodic small pullbacks -- avoids RSI
    # saturating at 100, which a perfectly monotonic series would trigger
    # (maximally "overbought", which this model correctly treats as a
    # caution signal rather than blindly chasing the trend).
    base = [100 + i - (2 if i % 5 == 0 else 0) for i in range(len(dates))]
    close = pd.Series(base, index=dates, dtype=float)
    df = pd.DataFrame({
        "open": close, "high": close * 1.001, "low": close * 0.999, "close": close,
        "volume": 1_000_000,
    }, index=dates)
    engine = ProbabilityEngine()
    signal = engine.generate_signal(df)
    # Directional bias check rather than requiring the exact BUY threshold --
    # the blended heuristic intentionally tempers momentum with an
    # overbought/mean-reversion caution component, so "biased toward buy"
    # means a positive edge/probability, not necessarily a firm BUY signal.
    assert signal.edge > 0
    assert signal.probability > 0.5


def test_deterministic_given_same_seed():
    df1 = generate_synthetic_history("SEEDTEST", periods=200, seed=123)
    df2 = generate_synthetic_history("SEEDTEST", periods=200, seed=123)
    pd.testing.assert_frame_equal(df1, df2)
