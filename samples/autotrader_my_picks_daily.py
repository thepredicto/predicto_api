import sys
sys.path.append("../predicto_api/")

from predicto_api_wrapper import PredictoApiWrapper, TradeAction
from alpaca_api_wrapper import AlpacaApiWrapper

# initialize alpaca api wrapper
alpaca_api_endpoint = 'https://paper-api.alpaca.markets' # use paper money endpoint for now (test env)
alpaca_api_key_id = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
alpaca_api_secret_key = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

alpaca_wrapper = AlpacaApiWrapper(alpaca_api_endpoint, alpaca_api_key_id, alpaca_api_secret_key)

# initialize predicto api wrapper
predicto_api_session_id = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
predicto_api_wrapper = PredictoApiWrapper(predicto_api_session_id)
predicto_api_wrapper.set_alpaca_api_wrapper(alpaca_wrapper)

# Autotrader parameters explanation
#   investmentAmountPerTrade : how much money to use per trade (note we'll submit an order for as many stocks as possible up to this number. If it's not enough for a single stock we'll skip)

# Execute Predicto AutoTrader using "My Picks" as you picked them in Predicto website!
# Manually pick them in https://predic.to/autotrader, explore them in https://predic.to/exploreroi?my=1
# You can schedule this script to run daily before market open (6.30am E.T.), it will submit last day's "My Picks"
# Note: Make sure you understand the risks if you are using real money!
predicto_api_wrapper.submit_my_latest_trade_picks(
                                        investmentAmountPerTrade=1000)