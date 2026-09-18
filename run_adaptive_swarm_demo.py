import os
from live_config import INITIAL_CAPITAL, MAX_DAILY_DRAWDOWN_PCT, MAX_LEVERAGE, MAINTENANCE_MARGIN_PCT

print('ADAPTIVE LIVE SWARM ENGAGED')
deployable = INITIAL_CAPITAL
guardrails = {
    'max_daily_drawdown_pct': MAX_DAILY_DRAWDOWN_PCT,
    'max_leverage': MAX_LEVERAGE,
    'maintenance_margin_pct': MAINTENANCE_MARGIN_PCT
}

allocations = {
    'mean_reversion': deployable * 0.25,
    'momentum': deployable * 0.35,
    'signal_matrix': deployable * 0.40
}

print('[t=00] deployable=$' + f'{deployable:.2f}' + ' guardrails=' + str(guardrails) + ' allocations=' + str(allocations))
print('Final live target equity: $' + f'{deployable:.2f}')
