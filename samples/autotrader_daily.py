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
#   abs_change_pct_threshold : the absolute percentage expected change threshold, default is 0.02 (2%)
#   actions                  : array with actions filter, default is [int(TradeAction.Buy), int(TradeAction.Sell)]
#   average_uncertainty      : threshold for average uncertainty of forecast - the higher the riskier, default 0.15 (15%)
#   model_avg_roi            : threshold for the historical average ROI for all the Trade Picks from the stock's model, default 0.0 (non negative ROI)
#   symbols                  : array with symbols to trade, if None all of them will be considered
#   investmentAmountPerTrade : how much money to use per trade (note we'll submit an order for as many stocks as possible up to this number. If it's not enough for a single stock we'll skip)

# Execute Predicto AutoTrader!
# You can schedule this script to run daily before market open (6.30am E.T.)
# Note: Make sure you understand the risks if you are using real money!
predicto_api_wrapper.submit_latest_trade_picks(
                                        abs_change_pct_threshold = 0.02,
                                        actions = [int(TradeAction.Buy), int(TradeAction.Sell)],
                                        average_uncertainty = 0.15,
                                        model_avg_roi = 0.0,
                                        symbols = None,
                                        investmentAmountPerTrade=1000)