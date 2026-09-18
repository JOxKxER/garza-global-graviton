import os
import sys
import json
import uuid
from webull.core.client import ApiClient
from webull.trade.trade_client import TradeClient

def build_stock_order(symbol, instrument_id, quantity, side="BUY", order_type="MARKET", price=None, time_in_force="DAY"):
    order = {
        "client_order_id": str(uuid.uuid4()),
        "symbol": symbol.upper(),
        "instrument_id": str(instrument_id),
        "market": "US",
        "instrument_type": "EQUITY",
        "side": side.upper(),
        "order_type": order_type.upper(),
        "quantity": str(quantity),
        "time_in_force": time_in_force.upper()
    }
    if price is not None and order_type.upper() in ["LMT", "LIMIT"]:
        order["price"] = str(price)
    return [order]

def main():
    app_key = os.environ.get("WEBULL_APP_KEY")
    app_secret = os.environ.get("WEBULL_APP_SECRET")
    account_id = os.environ.get("WEBULL_ACCOUNT_ID")
    instrument_id = os.environ.get("WEBULL_INSTRUMENT_ID")
    
    if not app_key or not app_secret:
        print("Error: WEBULL_APP_KEY and WEBULL_APP_SECRET environment variables must be set.")
        sys.exit(1)
    if not account_id:
        print("Error: WEBULL_ACCOUNT_ID environment variable must be set.")
        sys.exit(1)
    if not instrument_id:
        print("Set WEBULL_INSTRUMENT_ID or pass --instrument-id.")
        sys.exit(2)
        
    print("--- CONNECTING TO WEBULL SANDBOX API ---")
    api_client = ApiClient(app_key, app_secret, "us")
    api_client.add_endpoint("us", "api.sandbox.webull.com")
    
    trade_client = TradeClient(api_client)
    
    orders = build_stock_order("AAPL", instrument_id, 1)
    
    try:
        print("\nSending preview order request...")
        res = trade_client.order_v3.preview_order(account_id=account_id, preview_orders=orders)
        if res.status_code == 200:
            print("Preview Order Success:")
            print(json.dumps(res.json(), indent=2))
        else:
            print(f"API Error [{res.status_code}]: {res.text}")
            
        if "--place" in sys.argv:
            if os.environ.get("WEBULL_ALLOW_ORDER_PLACEMENT", "").lower() != "true":
                print("Order placement blocked: Set WEBULL_ALLOW_ORDER_PLACEMENT=true to execute.")
                return
            print("\nExecuting live sandbox order placement...")
            res_place = trade_client.order_v3.place_order(account_id=account_id, new_orders=orders)
            if res_place.status_code == 200:
                print("Order Placement Success:")
                print(json.dumps(res_place.json(), indent=2))
            else:
                print(f"Placement Error [{res_place.status_code}]: {res_place.text}")
    except Exception as e:
        print(f"Exception encountered: {e}")

if __name__ == "__main__":
    main()
