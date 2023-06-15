import alpaca_trade_api as tradeapi
import asyncio
import pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from alpaca_trade_api.stream import Stream

# Alpaca API
APCA_API_KEY_ID = ''
APCA_API_SECRET_KEY = ''
APCA_API_BASE_URL = 'https://paper-api.alpaca.markets'  # use paper trading URL for testing

api = tradeapi.REST(APCA_API_KEY_ID, APCA_API_SECRET_KEY, APCA_API_BASE_URL, api_version='v2')
conn = tradeapi.stream.Stream(APCA_API_KEY_ID, APCA_API_SECRET_KEY, base_url=APCA_API_BASE_URL)

# Define the EMA and RSI parameters
short_window = 13
long_window = 48
rsi_period = 14
rsi_upper = 54
rsi_lower = 46

# Define a DataFrame to store the prices
data = pd.DataFrame(columns=['price'])

async def on_trade_update(conn, channel, trade):
    global data
    print(f'received trade at {trade.price}')
    data = data.append({'price': trade.price}, ignore_index=True)

    # Ensure we have enough data to calculate short_window EMA, long_window EMA and RSI
    if len(data) > long_window + rsi_period:

        # Calculate the EMA and RSI
        data['ema_short'] = EMAIndicator(data['price'], short_window).ema_indicator()
        data['ema_long'] = EMAIndicator(data['price'], long_window).ema_indicator()
        data['rsi'] = RSIIndicator(data['price'], rsi_period).rsi()

        # Check for buy signal
        if data['ema_short'].iloc[-1] > data['ema_long'].iloc[-1] and data['rsi'].iloc[-1] > rsi_upper:
            cash = api.get_account().cash
            shares_to_buy = (float(cash) * 0.1) // data['price'].iloc[-1]  # 10% of holdings
            api.submit_order(
                symbol='SPY',
                qty=shares_to_buy,
                side='buy',
                type='market',
                time_in_force='gtc',
                order_class='trailing_stop',
                trail_percent='10'
            )

        # Check for sell signal
        elif data['ema_short'].iloc[-1] < data['ema_long'].iloc[-1] and data['rsi'].iloc[-1] < rsi_lower:
            shares_to_sell = api.get_account().portfolio_history().shares['SPY']
            api.submit_order(
                symbol='SPY',
                qty=shares_to_sell,
                side='sell',
                type='market',
                time_in_force='gtc',
                order_class='trailing_stop',
                trail_percent='10'
            )

def run():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        conn.subscribe(['trade_updates'], on_trade_update)
    )
