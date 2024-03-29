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
#   abs_change_pct_threshold : the absolute percentage expected change threshold, default is 0.02 (2%)
#   actions                  : array with actions filter, default is [int(TradeAction.Buy), int(TradeAction.Sell)]
#   average_uncertainty      : threshold for average uncertainty of forecast - the higher the riskier, default 0.15 (15%)
#   model_avg_roi            : threshold for the historical average ROI for all the Trade Picks from the stock's model, default 0.0 (non negative ROI)
#   symbols                  : array with symbols to trade, if None all of them will be considered
#   investment_per_trade     : how much money to use per trade (note we'll submit an order for as many stocks as possible up to this number. If it's not enough for a single stock we'll skip)
#   trade_order_type         : TradeOrderType.Bracket or TradeOrderType.TrailingStop. Bracket will set fixed stop loss and take profit prices. TrailingStop will set a trailing stop price.
#   stoploss_fixed_pct       : if provided, stoploss will be set at this fixed percentage (e.g. value 0.02 (2%) will set stoploss to -2% on a BUY order, and +2% on a SELL order)
 
# Execute Predicto AutoTrader!
# You can schedule this script to run daily before market open (9.30am E.T.)
# Note: Make sure you understand the risks if you are using real money!
predicto_api_wrapper.submit_latest_trade_picks(
    abs_change_pct_threshold = 0.02,
    actions = [int(TradeAction.Buy), int(TradeAction.Sell)],
    average_uncertainty = 0.15,
    model_avg_roi = 0.0,
    symbols = None,
    investment_per_trade=1000,
    trade_order_type=TradeOrderType.Bracket,
    stoploss_fixed_pct=None)