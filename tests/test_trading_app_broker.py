import pytest

from trading_app.execution.broker_client import PaperSimulationBroker


def test_starting_equity_matches_cash():
    broker = PaperSimulationBroker(starting_equity=10_000.0)
    assert broker.get_account_equity() == 10_000.0
    assert broker.is_market_open() is True


def test_buy_reduces_cash_and_opens_position():
    broker = PaperSimulationBroker(starting_equity=10_000.0)
    order = broker.submit_order("AAPL", quantity=10, side="BUY", price_hint=100.0)
    assert order.status == "FILLED"
    assert broker.cash == 9000.0
    position = broker.get_position("AAPL")
    assert position is not None
    assert position.quantity == 10
    assert position.avg_entry_price == 100.0


def test_buy_rejected_when_insufficient_cash():
    broker = PaperSimulationBroker(starting_equity=500.0)
    order = broker.submit_order("AAPL", quantity=10, side="BUY", price_hint=100.0)
    assert order.status == "REJECTED_INSUFFICIENT_CASH"
    assert order.quantity == 0
    assert broker.cash == 500.0


def test_sell_without_position_is_rejected():
    broker = PaperSimulationBroker(starting_equity=10_000.0)
    order = broker.submit_order("AAPL", quantity=5, side="SELL", price_hint=100.0)
    assert order.status == "REJECTED_NO_POSITION"


def test_sell_partial_quantity_capped_at_held_amount():
    broker = PaperSimulationBroker(starting_equity=10_000.0)
    broker.submit_order("AAPL", quantity=5, side="BUY", price_hint=100.0)
    order = broker.submit_order("AAPL", quantity=100, side="SELL", price_hint=110.0)
    assert order.status == "FILLED"
    assert order.quantity == 5  # capped, not the requested 100
    assert broker.get_position("AAPL") is None  # fully closed


def test_averaging_into_an_existing_position():
    broker = PaperSimulationBroker(starting_equity=10_000.0)
    broker.submit_order("AAPL", quantity=10, side="BUY", price_hint=100.0)
    broker.submit_order("AAPL", quantity=10, side="BUY", price_hint=110.0)
    position = broker.get_position("AAPL")
    assert position.quantity == 20
    assert position.avg_entry_price == pytest.approx(105.0)
