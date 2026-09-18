from datetime import datetime, timedelta

from trading_app.settlement.ledger import SettlementLedger, add_business_days


def test_add_business_days_skips_weekend():
    monday = datetime(2026, 1, 5)  # Monday
    friday_plus_one = add_business_days(datetime(2026, 1, 9), 1)  # Friday -> Monday
    assert friday_plus_one.weekday() == 0  # Monday
    assert add_business_days(monday, 1).weekday() == 1  # Tuesday


def test_sale_proceeds_are_not_settled_cash_immediately():
    ledger = SettlementLedger(settled_cash=1000.0)
    now = datetime(2026, 1, 5, 9, 30)
    ledger.record_sale_proceeds("AAPL", 500.0, now)
    assert ledger.settled_cash == 1000.0
    assert ledger.unsettled_total() == 500.0


def test_proceeds_settle_after_t_plus_1():
    ledger = SettlementLedger(settled_cash=1000.0, settlement_days=1)
    trade_time = datetime(2026, 1, 5, 9, 30)  # Monday
    ledger.record_sale_proceeds("AAPL", 500.0, trade_time)

    # Not yet settled same day
    ledger.process_settlements(trade_time + timedelta(hours=1))
    assert ledger.settled_cash == 1000.0

    # Settled the next business day
    settle_day = add_business_days(trade_time, 1)
    newly_settled = ledger.process_settlements(settle_day)
    assert newly_settled == 500.0
    assert ledger.settled_cash == 1500.0
    assert ledger.unsettled_total() == 0.0


def test_next_unlock_projects_soonest_pending_amount():
    ledger = SettlementLedger(settled_cash=0.0)
    t0 = datetime(2026, 1, 5, 9, 30)
    ledger.record_sale_proceeds("AAPL", 100.0, t0)
    ledger.record_sale_proceeds("MSFT", 200.0, t0 + timedelta(hours=2))
    upcoming = ledger.next_unlock(t0)
    assert upcoming is not None
    assert upcoming.amount == 100.0  # first trade settles first


def test_spend_settled_cash_rejects_insufficient_funds():
    ledger = SettlementLedger(settled_cash=100.0)
    assert ledger.spend_settled_cash(50.0) is True
    assert ledger.settled_cash == 50.0
    assert ledger.spend_settled_cash(1000.0) is False
    assert ledger.settled_cash == 50.0  # unchanged on rejection
