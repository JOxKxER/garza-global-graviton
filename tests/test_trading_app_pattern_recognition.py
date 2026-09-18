import numpy as np
import pandas as pd

from trading_app.analytics.pattern_recognition import PatternRecognitionEngine
from trading_app.data.ingestion import generate_synthetic_history


def _make_breakout_df(periods: int = 80) -> pd.DataFrame:
    """A flat-ish series with a sharp final breakout above the prior
    Donchian channel high, plus a volume spike on that final bar."""
    close = np.concatenate([np.full(periods - 1, 100.0), [130.0]])
    high = close * 1.001
    low = close * 0.999
    open_ = np.concatenate([[100.0], close[:-1]])
    volume = np.full(periods, 1_000_000.0)
    volume[-1] = 10_000_000.0
    index = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=periods)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=index
    )


def test_scan_returns_neutral_report_when_insufficient_history():
    engine = PatternRecognitionEngine()
    df = generate_synthetic_history("TST", periods=10, seed=1)
    report = engine.scan("TST", df)
    assert report.triggers == []
    assert report.volatility_regime == "NORMAL"
    assert report.net_direction == "NEUTRAL"


def test_scan_detects_donchian_breakout_and_volume_anomaly():
    engine = PatternRecognitionEngine(donchian_period=20)
    df = _make_breakout_df()
    report = engine.scan("TST", df)

    trigger_names = {t.name for t in report.triggers}
    assert "donchian_breakout_up" in trigger_names
    assert "volume_anomaly" in trigger_names
    assert report.net_direction == "BULLISH"
    assert report.agreement_ratio == 1.0


def test_scan_classifies_volatility_regime_on_realistic_series():
    engine = PatternRecognitionEngine()
    df = generate_synthetic_history("TST", periods=300, annual_volatility=0.25, seed=42)
    report = engine.scan("TST", df)
    assert report.volatility_regime in {"LOW", "NORMAL", "HIGH"}


def test_pattern_report_net_direction_neutral_with_no_triggers():
    from trading_app.analytics.pattern_recognition import PatternReport

    report = PatternReport(symbol="TST", volatility_regime="NORMAL", triggers=[])
    assert report.net_direction == "NEUTRAL"
    assert report.agreement_ratio == 0.0
