from trading_app.analytics.adaptive_strategy import (
    AdaptiveStrategyController,
    MAX_RISK_MULTIPLIER,
    MIN_RISK_MULTIPLIER,
)
from trading_app.analytics.pattern_recognition import PatternReport, TriggerMarker


def test_high_volatility_regime_reduces_risk_and_raises_probability_bar():
    controller = AdaptiveStrategyController()
    report = PatternReport(symbol="TST", volatility_regime="HIGH", triggers=[])
    adapted = controller.adapt(report)

    assert adapted.risk_multiplier < 1.0
    assert adapted.probability_threshold_delta > 0.0
    assert adapted.stop_loss_multiplier > 1.0


def test_low_volatility_regime_increases_risk_and_lowers_probability_bar():
    controller = AdaptiveStrategyController()
    report = PatternReport(symbol="TST", volatility_regime="LOW", triggers=[])
    adapted = controller.adapt(report)

    assert adapted.risk_multiplier > 1.0
    assert adapted.probability_threshold_delta < 0.0


def test_confirmed_trend_boosts_risk_multiplier_further():
    controller = AdaptiveStrategyController()
    confirmed = PatternReport(
        symbol="TST",
        volatility_regime="NORMAL",
        triggers=[
            TriggerMarker("donchian_breakout_up", "BULLISH", 1.0),
            TriggerMarker("golden_cross", "BULLISH", 0.8),
        ],
    )
    baseline = PatternReport(symbol="TST", volatility_regime="NORMAL", triggers=[])

    adapted_confirmed = controller.adapt(confirmed)
    adapted_baseline = controller.adapt(baseline)
    assert adapted_confirmed.risk_multiplier > adapted_baseline.risk_multiplier


def test_conflicting_triggers_reduce_risk_multiplier():
    controller = AdaptiveStrategyController()
    conflicting = PatternReport(
        symbol="TST",
        volatility_regime="NORMAL",
        triggers=[
            TriggerMarker("donchian_breakout_up", "BULLISH", 1.0),
            TriggerMarker("death_cross", "BEARISH", 1.0),
        ],
    )
    baseline = PatternReport(symbol="TST", volatility_regime="NORMAL", triggers=[])

    adapted_conflicting = controller.adapt(conflicting)
    adapted_baseline = controller.adapt(baseline)
    assert adapted_conflicting.risk_multiplier < adapted_baseline.risk_multiplier


def test_risk_multiplier_always_within_bounds():
    controller = AdaptiveStrategyController()
    for regime in ("LOW", "NORMAL", "HIGH"):
        for triggers in (
            [],
            [TriggerMarker("x", "BULLISH", 1.0), TriggerMarker("y", "BULLISH", 1.0)],
            [TriggerMarker("x", "BULLISH", 1.0), TriggerMarker("y", "BEARISH", 1.0)],
        ):
            adapted = controller.adapt(PatternReport(symbol="TST", volatility_regime=regime, triggers=triggers))
            assert MIN_RISK_MULTIPLIER <= adapted.risk_multiplier <= MAX_RISK_MULTIPLIER
