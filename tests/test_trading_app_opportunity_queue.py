from datetime import datetime, timedelta

from trading_app.analytics.probability_engine import Action, Signal
from trading_app.settlement.opportunity_queue import OpportunityQueue, StagedOpportunity


def _make_opportunity(symbol, probability, edge, notional, staged_at):
    signal = Signal(action=Action.BUY, probability=probability, edge=edge, price=100.0, reasons=[])
    return StagedOpportunity(symbol=symbol, signal=signal, notional_required=notional, staged_at=staged_at)


def test_higher_alpha_opportunity_pops_first():
    queue = OpportunityQueue()
    now = datetime(2026, 1, 5, 9, 30)
    queue.stage(_make_opportunity("LOW", probability=0.55, edge=0.1, notional=1000, staged_at=now))
    queue.stage(_make_opportunity("HIGH", probability=0.9, edge=0.8, notional=1000, staged_at=now))

    best = queue.pop_best_affordable(now, available_buying_power=10_000)
    assert best is not None
    assert best.symbol == "HIGH"


def test_skips_unaffordable_opportunity_for_a_cheaper_one():
    queue = OpportunityQueue()
    now = datetime(2026, 1, 5, 9, 30)
    queue.stage(_make_opportunity("EXPENSIVE", probability=0.9, edge=0.9, notional=50_000, staged_at=now))
    queue.stage(_make_opportunity("AFFORDABLE", probability=0.6, edge=0.2, notional=500, staged_at=now))

    best = queue.pop_best_affordable(now, available_buying_power=1000)
    assert best is not None
    assert best.symbol == "AFFORDABLE"
    # The expensive one should still be in the queue for later, not dropped
    assert len(queue) == 1


def test_stale_opportunity_is_dropped_not_executed():
    queue = OpportunityQueue(max_staleness_seconds=60)
    staged_at = datetime(2026, 1, 5, 9, 30)
    queue.stage(_make_opportunity("STALE", probability=0.9, edge=0.9, notional=100, staged_at=staged_at))

    later = staged_at + timedelta(seconds=120)
    result = queue.pop_best_affordable(later, available_buying_power=10_000)
    assert result is None
    assert len(queue) == 0


def test_pop_best_affordable_returns_none_when_empty():
    queue = OpportunityQueue()
    assert queue.pop_best_affordable(datetime.now(), available_buying_power=10_000) is None
