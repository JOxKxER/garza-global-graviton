import os
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

API_KEY = "PKWB7NXPCSBNCDOUZ5AST677AE"
SECRET_KEY = "86mZ79o9X7aKBoaJ9TJnH3JLRkkZK6eNKfKknt"

print("--- CONNECTING TO ALPACA PAPER TRADING ---")
client = TradingClient(api_key=API_KEY, secret_key=SECRET_KEY, paper=True, url_override="https://paper-api.alpaca.markets")

account = client.get_account()
print(f"Connected successfully! Status: {account.status}, Cash Balance: ${float(account.cash):.2f}")

allocations = {"AAPL": 35.0, "MSFT": 40.0, "SPY": 25.0}
for symbol, amount in allocations.items():
    try:
        order = client.submit_order(
            order_data=MarketOrderRequest(
                symbol=symbol,
                notional=round(amount, 2),
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
        )
        print(f"  -> Submitted fractional order: ${amount:.2f} of {symbol}")
    except Exception as e:
        print(f"  -> Error ordering {symbol}: {e}")

print("Execution complete!")
