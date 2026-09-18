import sys
from live_config import INITIAL_CAPITAL, TRADING_MODE, MAX_DAILY_DRAWDOWN_PCT

print(f"--- ACTIVE LIVE SWARM ENGINE [{TRADING_MODE.upper()} MODE] ---")
print(f"Target Initial Capital: ")

allocations = {
    'mean_reversion': INITIAL_CAPITAL * 0.25,
    'momentum': INITIAL_CAPITAL * 0.35,
    'signal_matrix': INITIAL_CAPITAL * 0.40
}

print("Scaled Micro-Lot Allocations for Live Capital:")
for strategy, amount in allocations.items():
    print(f"  -> {strategy}: ")
