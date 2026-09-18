import os, json
from datetime import datetime

LEDGER_FILE = 'swarm_intelligence_ledger.json'

def log_external_pattern(source_id, asset, direction, confidence_score, rationale):
    os.makedirs('data_inbox', exist_ok=True)
    entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'source_id': source_id,
        'asset': asset,
        'direction': direction,
        'confidence': confidence_score,
        'rationale': rationale,
        'status': 'tracked'
    }
    
    ledger = []
    if os.path.exists(LEDGER_FILE):
        try:
            with open(LEDGER_FILE, 'r', encoding='utf-8') as f:
                ledger = json.load(f)
        except Exception:
            ledger = []
            
    ledger.append(entry)
    with open(LEDGER_FILE, 'w', encoding='utf-8') as f:
        json.dump(ledger, f, indent=2)
    print(f'Successfully logged pattern from [{source_id}] on {asset} -> {direction}')

if __name__ == '__main__':
    log_external_pattern('AlphaWhale_99', 'BTC-USD', 'BUY', 0.89, 'Unusual volume spike & liquidity sweep detected.')
