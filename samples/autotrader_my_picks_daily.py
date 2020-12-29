import sys
sys.path.append("../predicto_api/")

from predicto_api_wrapper import PredictoApiWrapper, TradeAction, TradeOrderType
from alpaca_api_wrapper import AlpacaApiWrapper

# initialize alpaca api wrapper
alpaca_api_endpoint = 'https://paper-api.alpaca.markets' # use paper money endpoint for now (test env)
alpaca_api_key_id = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
alpaca_api_secret_key = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

alpaca_wrapper = AlpacaApiWrapper(alpaca_api_endpoint, alpaca_api_key_id, alpaca_api_secret_key)

# initialize predicto api wrapper
predicto_api_key = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
predicto_api_wrapper = PredictoApiWrapper(predicto_api_key)
predicto_api_wrapper.set_alpaca_api_wrapper(alpaca_wrapper)

# Autotrader parameters explanation
#   investment_per_trade : how much money to use per trade (note we'll submit an order for as many stocks as possible up to this number. If it's not enough for a single stock we'll skip)
#   trade_order_type     : TradeOrderType.Bracket or TradeOrderType.TrailingStop. Bracket will set fixed stop loss and take profit prices. TrailingStop will set a trailing stop price.

# Execute Predicto AutoTrader using "My Picks" as you picked them in Predicto website!
# Manually pick them in https://predic.to/autotrader, explore them in https://predic.to/exploreroi?my=1
# You can schedule this script to run daily before market open (9.30am E.T.), it will submit last day's "My Picks"
# Note: Make sure you understand the risks if you are using real money!
predicto_api_wrapper.submit_my_latest_trade_picks(
    investment_per_trade=1000,
    trade_order_type=TradeOrderType.Bracket)