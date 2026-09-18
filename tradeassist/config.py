"""TradeAssist configuration.

Exposes a module-level ``config`` dict so consumers can do::

    from config import config
    config["position_sizing_threshold"]
"""

config = {
    # Maximum fraction of account equity a single position may occupy
    # before the analyzer flags it as oversized.
    "position_sizing_threshold": 0.05,
}
