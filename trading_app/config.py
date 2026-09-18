"""Environment-driven configuration. Safe-by-default: the app can only place
live orders if TWO separate environment variables both explicitly opt in
(TRADING_MODE=live AND ALLOW_LIVE_TRADING=true) -- a single typo or forgotten
variable falls back to paper mode, never the other way around.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv is a convenience, not a hard requirement


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    return float(value) if value else default


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class TradingConfig:
    # --- Broker credentials (never hardcode these; env vars only) ---
    alpaca_api_key: str = field(default_factory=lambda: os.environ.get("ALPACA_API_KEY", ""))
    alpaca_secret_key: str = field(default_factory=lambda: os.environ.get("ALPACA_SECRET_KEY", ""))
    alpaca_base_url: str = field(
        default_factory=lambda: os.environ.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
    )

    # --- Mode: defaults to paper; live requires a double opt-in ---
    trading_mode: str = field(default_factory=lambda: os.environ.get("TRADING_MODE", "paper").lower())
    allow_live_trading: bool = field(default_factory=lambda: _env_bool("ALLOW_LIVE_TRADING", False))

    # --- Universe ---
    symbols: List[str] = field(
        default_factory=lambda: [
            s.strip() for s in os.environ.get("TRADING_SYMBOLS", "AAPL,MSFT,SPY").split(",") if s.strip()
        ]
    )

    # --- Risk management (conservative defaults; see risk/risk_manager.py
    #     for the hard ceilings that apply regardless of these values) ---
    risk_per_trade_pct: float = field(default_factory=lambda: _env_float("RISK_PER_TRADE_PCT", 0.01))
    kelly_fraction: float = field(default_factory=lambda: _env_float("KELLY_FRACTION", 0.5))
    stop_loss_pct: float = field(default_factory=lambda: _env_float("STOP_LOSS_PCT", 0.02))
    take_profit_pct: float = field(default_factory=lambda: _env_float("TAKE_PROFIT_PCT", 0.04))
    max_daily_drawdown_pct: float = field(
        default_factory=lambda: _env_float("MAX_DAILY_DRAWDOWN_PCT", 0.03)
    )
    min_signal_probability: float = field(
        default_factory=lambda: _env_float("MIN_SIGNAL_PROBABILITY", 0.58)
    )

    # --- Settlement / account-type compliance (defaults to the SAFER cash
    #     account model; margin must be explicitly opted into) ---
    account_type: str = field(default_factory=lambda: os.environ.get("ACCOUNT_TYPE", "cash").lower())
    settlement_days: int = field(default_factory=lambda: int(os.environ.get("SETTLEMENT_DAYS", "1")))
    max_leverage: float = field(default_factory=lambda: _env_float("MAX_LEVERAGE", 2.0))
    maintenance_margin_pct: float = field(
        default_factory=lambda: _env_float("MAINTENANCE_MARGIN_PCT", 0.25)
    )
    pdt_equity_threshold: float = field(
        default_factory=lambda: _env_float("PDT_EQUITY_THRESHOLD", 25_000.0)
    )
    opportunity_staleness_seconds: float = field(
        default_factory=lambda: _env_float("OPPORTUNITY_STALENESS_SECONDS", 300.0)
    )

    # --- Local data cache ---
    cache_dir: str = field(default_factory=lambda: os.environ.get("TRADING_CACHE_DIR", "trading_app_cache"))

    @property
    def is_live(self) -> bool:
        """Only True if BOTH TRADING_MODE=live and ALLOW_LIVE_TRADING=true are
        set. Missing/misconfigured env vars always fail safe into paper mode."""
        return self.trading_mode == "live" and self.allow_live_trading

    def require_credentials_for_live(self) -> None:
        if self.is_live and not (self.alpaca_api_key and self.alpaca_secret_key):
            raise RuntimeError(
                "Live trading requested (TRADING_MODE=live, ALLOW_LIVE_TRADING=true) "
                "but ALPACA_API_KEY/ALPACA_SECRET_KEY are not set. Refusing to start "
                "live with no credentials rather than silently falling back."
            )
