import os
import json
from webull.core.client import ApiClient
from webull.trade.trade_client import TradeClient

# Load production credentials from environment variables
API_KEY = os.environ.get("WEBULL_LIVE_APP_KEY", "YOUR_LIVE_APP_KEY")
SECRET_KEY = os.environ.get("WEBULL_LIVE_SECRET_KEY", "YOUR_LIVE_SECRET_KEY")

print("--- CONNECTING TO WEBULL LIVE PRODUCTION API ---")
api_client = ApiClient(API_KEY, SECRET_KEY, "us")
# Default production endpoint (no sandbox override)

trade_client = TradeClient(api_client)

try:
    print("Fetching live account list...")
    res = trade_client.account_v2.get_account_list()
    if res.status_code == 200:
        accounts = res.json()
        print(f"Found {len(accounts)} live accounts.")
        print(json.dumps(accounts, indent=2))
        
        # Select your live cash/margin account ID here
        # target_account_id = accounts[0]['account_id']
    else:
        print(f"API Error: {res.status_code} - {res.text}")
except Exception as e:
    print(f"Exception: {e}")
