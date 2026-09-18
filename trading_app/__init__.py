"""
trading_app - Local, air-gapped automated trading engine for personal use.

>>> IMPORTANT DISCLAIMER <<<
This is not financial advice. Automated trading carries substantial risk of
financial loss, including total loss of deposited capital. Backtests and
probability estimates produced by this engine are heuristic and do not
guarantee future performance. You are solely responsible for any capital you
connect to a live broker account. Always validate extensively in paper mode
first, understand the tax/regulatory obligations in your jurisdiction, and
never risk money you cannot afford to lose.

Module layout:
    config.py            Environment-driven configuration, safe-by-default.
    data/ingestion.py     Historical/local data loading + on-disk caching.
    analytics/probability_engine.py   Indicator computation + signal generation.
    risk/risk_manager.py  Position sizing, stop-loss/take-profit, drawdown breaker.
    execution/broker_client.py   Broker abstraction: PaperSimulationBroker (default,
                          zero network calls) and AlpacaBroker (opt-in, live/paper).
    engine.py             Wires the four modules together into one trading loop.

The probability/risk decision path (data already cached locally -> indicators
-> signal -> position size -> stop/take levels) never makes a network call --
only the ingestion module's *optional* live-fetch path and the AlpacaBroker's
order submission touch the network, and both are opt-in and clearly isolated.
"""
