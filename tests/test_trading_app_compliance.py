from datetime import date

from trading_app.settlement.compliance import (
    AccountType,
    ComplianceGuardrails,
    DayTradeTracker,
    MarginMonitor,
    PDT_MAX_DAY_TRADES_PER_5_SESSIONS,
)
from trading_app.settlement.ledger import SettlementLedger


def test_cash_account_rejects_buy_exceeding_settled_cash():
    guardrails = ComplianceGuardrails(account_type=AccountType.CASH)
    ledger = SettlementLedger(settled_cash=1000.0)
    ledger.record_sale_proceeds("AAPL", 5000.0, date(2026, 1, 5))  # unsettled, shouldn't count

    violation = guardrails.check_buy(ledger, notional=1500.0)
    assert violation is not None
    assert "settled cash" in violation

    ok = guardrails.check_buy(ledger, notional=500.0)
    assert ok is None


def test_margin_account_has_no_settled_cash_restriction():
    guardrails = ComplianceGuardrails(account_type=AccountType.MARGIN)
    ledger = SettlementLedger(settled_cash=0.0)
    assert guardrails.check_buy(ledger, notional=10_000.0) is None


def test_day_trade_tracker_counts_within_rolling_window():
    tracker = DayTradeTracker(window_sessions=5)
    for i in range(2):
        tracker.record_day_trade(date(2026, 1, 5 + i))
    assert tracker.count_in_window(date(2026, 1, 7)) == 2
    assert not tracker.would_exceed_pdt_limit(date(2026, 1, 7))

    # A 3rd day trade brings the count to the limit -- a 4th would now be blocked.
    tracker.record_day_trade(date(2026, 1, 7))
    assert tracker.would_exceed_pdt_limit(date(2026, 1, 7))


def test_pdt_limit_blocks_fourth_day_trade_under_25k_margin():
    guardrails = ComplianceGuardrails(account_type=AccountType.MARGIN)
    as_of = date(2026, 1, 9)
    for i in range(PDT_MAX_DAY_TRADES_PER_5_SESSIONS):
        guardrails.day_trade_tracker.record_day_trade(date(2026, 1, 5 + i))

    violation = guardrails.check_day_trade_limit(equity=10_000.0, as_of=as_of)
    assert violation is not None
    assert "PDT" in violation


def test_pdt_limit_does_not_apply_above_25k_equity():
    guardrails = ComplianceGuardrails(account_type=AccountType.MARGIN)
    as_of = date(2026, 1, 9)
    for i in range(PDT_MAX_DAY_TRADES_PER_5_SESSIONS):
        guardrails.day_trade_tracker.record_day_trade(date(2026, 1, 5 + i))

    assert guardrails.check_day_trade_limit(equity=50_000.0, as_of=as_of) is None


def test_pdt_limit_does_not_apply_to_cash_accounts():
    guardrails = ComplianceGuardrails(account_type=AccountType.CASH)
    as_of = date(2026, 1, 9)
    for i in range(10):
        guardrails.day_trade_tracker.record_day_trade(date(2026, 1, 5 + i))
    assert guardrails.check_day_trade_limit(equity=1000.0, as_of=as_of) is None


def test_margin_monitor_flags_excess_leverage():
    monitor = MarginMonitor(max_leverage=2.0)
    assert monitor.check_leverage(equity=10_000.0, gross_position_value_after_trade=25_000.0) is not None
    assert monitor.check_leverage(equity=10_000.0, gross_position_value_after_trade=15_000.0) is None


def test_margin_monitor_flags_maintenance_call():
    monitor = MarginMonitor(maintenance_margin_pct=0.25)
    assert monitor.check_maintenance_margin(equity=2000.0, margin_used=10_000.0) is not None  # 20% < 25%
    assert monitor.check_maintenance_margin(equity=3000.0, margin_used=10_000.0) is None  # 30% >= 25%
