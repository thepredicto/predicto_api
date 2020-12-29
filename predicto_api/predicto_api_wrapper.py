import enum
import matplotlib.pyplot as plt
import pandas as pd
import requests
from datetime import datetime, timedelta
import time

class TradeAction(enum.IntEnum):
    Noaction = 0
    Buy = 1
    Sell = 2

class TradeOrderType(enum.IntEnum):
    Market = 0
    Bracket = 1
    TrailingStop = 2

class PredictoApiWrapper(object):
    """
    Api wrapper class for Predicto (https://predic.to)
    """
    
    _base_url = 'https://predic.to'

    def __init__(self, api_key):
        self._head = {'X-Predicto-Api-Key': api_key}
        self._alpaca_api_wrapper = None

    def set_alpaca_api_wrapper(self, alpaca_api_wrapper):
        """Sets the alpaca api wrapper object. It will be used to submit orders to Alpaca.
        
        Args:
            alpaca_api_wrapper : The AlpacaApiWrapper object to use
        """
        self._alpaca_api_wrapper = alpaca_api_wrapper

    def get_supported_tickers(self):
        """Returns a list of supported tickers
        
        Args:
            return_pandas_df : returns a pandas dataframe if True, json otherwise
        
        Returns:
            json with all the supported tickers
        """
        endpoint = "{0}/stocks/allwithforecast".format(PredictoApiWrapper._base_url)
        jsn = requests.get(endpoint, headers=self._head).json()
        
        return jsn
    
    def get_forecast(self, ticker, date):
        """Returns the forecast of the selected ticker for selected date
        
        Args:
            ticker : the ticker of the stock
            date   : the date of the forecast (YYYY-MM-DD format)
        
        Returns:
            json with retrieved forecast
        """
        endpoint = "{0}/api/forecasting/{1}/{2}/-1".format(PredictoApiWrapper._base_url, ticker, date)
        jsn = requests.get(endpoint, headers=self._head).json()
        
        forecasting_json = jsn[0]['PredictionsJson'] if len(jsn) > 0 else None
        
        return forecasting_json
    
    def get_trade_pick(self, ticker, date):
        """Returns generated trade pick of the selected ticker for selected date based on that date's forecast
        
        Args:
            ticker : the ticker of the stock
            date   : the date of the forecast (YYYY-MM-DD format)
        
        Returns:
            json with retrieved trade pick
        """
        endpoint = "{0}/api/forecasting/tradepicks/{1}/{2}/_,0.0,0".format(PredictoApiWrapper._base_url, ticker, date)
        jsn = requests.get(endpoint, headers=self._head).json()
        
        trade_pick_json = jsn['Recommendations'][0] if len(jsn['Recommendations']) > 0 else None
        
        return trade_pick_json
        
    def get_my_trade_picks(self, date):
        """Returns a list of trade picks generated on given date that user has selected.
        As they appear in https://predic.to/exploreroi?my=1
        
        Args:
            date : the date of trade picks (YYYY-MM-DD format)
        
        Returns:
            json array with retrieved trade picks
        """
        endpoint = "{0}/api/forecasting/tradepicks/_/{1}/_,0.0,1".format(PredictoApiWrapper._base_url, date)
        jsn = requests.get(endpoint, headers=self._head).json()
        
        my_trade_picks_json = jsn['Recommendations']
        
        return my_trade_picks_json
            
    def get_model_recent_performance_graph(self, ticker):
        """Returns recent performance GIF url for selected ticker
        
        Args:
            ticker : the ticker of the stock
        
        Returns:
            the gif URL
        """
        endpoint = "{0}/api/history/blobs/{1}".format(PredictoApiWrapper._base_url, ticker)
        jsn = requests.get(endpoint, headers=self._head).json()

        return jsn[0]['ForecastModelGifBlobUrl'].split("?")[0]

    def get_forecast_and_tradepick_info(self, ticker, date, print_it=False):
        """Helper method to retrieve forecast and trade pick for given ticker and date
        
        Args:
            ticker   : the ticker of the stock
            date     : the date of the forecast (YYYY-MM-DD format)
            print_it : whether to print retrieved info and plot
        
        Returns:
            The forecast json and trade pick json as (forecast_json, trade_pick_json)
        """
        # retrieve forecast and trade pick
        forecast_json = self.get_forecast(ticker, date)
        trade_pick_json = self.get_trade_pick(ticker, date)
        
        if print_it:
            print('Forecast for {0} on {1}'.format(ticker, date))

            if forecast_json is not None:
                # convert to pandas dataframe and plot forecast
                forecast_df = pd.read_json(forecast_json, orient='index')
                forecast_df.Prediction.plot()
                plt.show()

                # print forecast info
                print(forecast_df[['Prediction', 'Uncertainty']])
                print()

            if trade_pick_json is not None:
                # print trade pick info
                predicted_change_percent = (trade_pick_json['TargetSellPrice'] - trade_pick_json['StartingPrice']) / trade_pick_json['StartingPrice']
                print('Trade Pick generated based on forecast for {0} on {1}'.format(ticker, date))
                print('---------------------------------------')
                print('Action          : \t{0}'.format(TradeAction(trade_pick_json['TradeAction']).name))
                print('Entry price     : \t{0}'.format(trade_pick_json['StartingPrice']))
                print('Target price    : \t{0}'.format(trade_pick_json['TargetSellPrice']))
                print('StopLoss price  : \t{0}'.format(trade_pick_json['TargetStopLossPrice']))
                print('Expiration Date : \t{0}'.format(trade_pick_json['ExpirationDate']))
                print('Predicted change: \t{0:.2f} %'.format(predicted_change_percent * 100))
                print('---------------------------------------')
                print()
                print()
        
        return (forecast_json, trade_pick_json)

    def submit_latest_trade_picks(      self, 
                                        abs_change_pct_threshold = 0.02,
                                        actions = [int(TradeAction.Buy), int(TradeAction.Sell)],
                                        average_uncertainty = 0.15,
                                        model_avg_roi = 0.0,
                                        symbols = None,
                                        investment_per_trade = 1000,
                                        trade_order_type = TradeOrderType.Bracket):
        """Call this daily just before market open (or during). It will use last day's Trade Picks.
        
        Args:
            abs_change_pct_threshold : the absolute percentage expected change threshold, default is 0.02 (2%)
            actions                  : array with actions filter, default is [int(TradeAction.Buy), int(TradeAction.Sell)]
            average_uncertainty      : threshold for average uncertainty of forecast - the higher the riskier, default 0.15 (15%)
            model_avg_roi            : threshold for the historical average ROI for all the Trade Picks from the stock's model, default 0.0 (non negative ROI)
            symbols                  : array with symbols to trade, if None all of them will be considered
            investment_per_trade     : how much money to use per trade (note we'll submit an order for as many stocks as possible up to this number. If it's not enough for a single stock we'll skip)
            trade_order_type         : one of TradeOrderType.Bracket or TradeOrderType.TrailingStop. Bracket will set fixed stop loss and take profit prices. TrailingStop will set a trailing stop price.
        """
        # retrieve all supported stocks
        stocks_json = self.get_supported_tickers()
        stocks_df = pd.DataFrame(stocks_json)
        # Filter based on given symbols list
        if (symbols is not None):
            stocks_df = stocks_df[stocks_df.RelatedSymbol.isin(symbols)]

        # get Trade Picks that were generated yesterday
        generated_date = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        print('Processing Predicto Trade Picks from {0}'.format(generated_date))
        print('- More details http://predic.to/exploreroi?minroi=0&sdate={0}'.format(generated_date))
        print()
        print('Using filters')
        print('\t abs_change_pct_threshold : {0:.2f}'.format(abs_change_pct_threshold))
        print('\t average_uncertainty      : {0:.2f}'.format(average_uncertainty))
        print('\t model_avg_roi            : {0:.2f}'.format(model_avg_roi))
        print('\t symbols                  : {0}'.format('All' if symbols is None else str(symbols)))
        print('\t actions                  : {0}'.format(str([TradeAction(x).name for x in actions])))
        print()

        symbols_submitted = []
        idx = 0
        for symbol in stocks_df.RelatedStock:
            idx += 1
            print('Processing {0}/{1}, Symbol: {2}'.format(idx, len(stocks_df), symbol))

            try:
                tp_json = self.get_trade_pick(symbol, generated_date)

                # Check if we got info back
                if tp_json is None:
                    print('\t        Trade Pick json is None. Not found or not generated yet. Try again later.')
                    continue

                change_pct = (tp_json['TargetSellPrice'] - tp_json['StartingPrice']) / tp_json['StartingPrice']

                # Check if filters are matched
                if abs(change_pct) >= abs_change_pct_threshold \
                        and tp_json['TradeAction'] in actions \
                        and tp_json['AvgUncertainty'] <= average_uncertainty \
                        and tp_json['AverageROI'] >= model_avg_roi:
                        
                    print('\tMatched Expected change : {0:.2f}% !'.format(change_pct * 100))
                    print('\t        Trade Action    : {0} !'.format(TradeAction(tp_json['TradeAction']).name))
                    print('\t        Avg Uncertainty : {0:.2f}% !'.format(tp_json['AvgUncertainty'] * 100))
                    print('\t        Avg ROI of model: {0:.2f}% !'.format(tp_json['AverageROI'] * 100))

                    # Create a client order id, for easy tracking
                    client_order_id = 'Predicto__{0}_{1}_{2}_{3}_bracket'.format(
                        generated_date,
                        datetime.today().strftime('%H-%M-%S'),
                        symbol, 
                        TradeAction(tp_json['TradeAction']).name)

                    # If all looks good, we can now submit our bracket order (market order + stop loss + take profit)
                    print()
                    print('> Alpaca: Submitting {0} order...'.format(trade_order_type.name))
                    print('------------------------') 
                    alpaca_order_result = self._alpaca_api_wrapper.submit_order(
                        trade_order_type,
                        TradeAction(tp_json['TradeAction']), 
                        symbol, 
                        None, 
                        investment_per_trade, 
                        tp_json['StartingPrice'], 
                        tp_json['TargetSellPrice'], 
                        tp_json['TargetStopLossPrice'], 
                        client_order_id)
                    print('------------------------')
                    print()

                    if alpaca_order_result is not None:
                        # unpack in case we want to process or store those values
                        (alpaca_order, newStartingPrice, newTargetPrice, newStopLossPrice, trailing_percent, newQuantity) = alpaca_order_result
                        # add it to our 'submitted' list
                        symbols_submitted.append(symbol)

                else:
                    print('\tSkipping, didnt match criteria\n')
                
                # make sure you sleep a bit to avoid hitting api limit
                time.sleep(1)
                    
            except Exception as ex:
                print('\t Skipping: Exception: {0}\n'.format(ex))

        print('Submitted {0} hedged orders: {1}'.format(len(symbols_submitted), str(symbols_submitted)))

    def submit_my_latest_trade_picks(self, investment_per_trade, trade_order_type):
        """Call this daily just before market open (or during). It will use last day's Trade Picks that YOU have picked in Predicto website.
        You can select your Trade Picks in https://predic.to/autotrader
        You can see your latest Trade picks in https://predic.to/exploreroi?my=1

        Args:
            investment_per_trade : how much money to use per trade (note we'll submit an order for as many stocks as possible up to this number. If it's not enough for a single stock we'll skip)
            trade_order_type     : one of TradeOrderType.Bracket or TradeOrderType.TrailingStop. Bracket will set fixed stop loss and take profit prices. TrailingStop will set a trailing stop price.
        """
        # get Trade Picks that were picked yesterday
        generated_date = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        print('Processing Predicto "My" Trade Picks from {0}'.format(generated_date))
        print('- More details https://predic.to/exploreroi?my=1&sdate={0}'.format(generated_date))
        print()

        # retrieve My Trade Picks
        tp_json_array = self.get_my_trade_picks(generated_date)

        symbols_submitted = []
        idx = 0
        for tp_json in tp_json_array:
            symbol = tp_json['Symbol']
            idx += 1
            print('Processing {0}/{1}, Symbol: {2}'.format(idx, len(tp_json_array), tp_json['Symbol']))

            try:
                change_pct = (tp_json['TargetSellPrice'] - tp_json['StartingPrice']) / tp_json['StartingPrice']

                print('\t Expected change : {0:.2f}% !'.format(change_pct * 100))
                print('\t Trade Action    : {0} !'.format(TradeAction(tp_json['TradeAction']).name))
                print('\t Avg Uncertainty : {0:.2f}% !'.format(tp_json['AvgUncertainty'] * 100))
                print('\t Avg ROI of model: {0:.2f}% !'.format(tp_json['AverageROI'] * 100))

                # Create a client order id, for easy tracking
                client_order_id = 'Predicto__{0}_{1}_{2}_{3}_bracket'.format(
                    generated_date,
                    datetime.today().strftime('%H-%M-%S'),
                    symbol, 
                    TradeAction(tp_json['TradeAction']).name)

                # If all looks good, we can now submit our bracket order (market order + stop loss + take profit)
                print()
                print('> Alpaca: Submitting {0} order...'.format(trade_order_type.name))
                print('------------------------')
                alpaca_order_result = self._alpaca_api_wrapper.submit_order(
                    trade_order_type,
                    TradeAction(tp_json['TradeAction']), 
                    symbol, 
                    None, 
                    investment_per_trade, 
                    tp_json['StartingPrice'], 
                    tp_json['TargetSellPrice'], 
                    tp_json['TargetStopLossPrice'], 
                    client_order_id)
                print('------------------------')
                print()

                if alpaca_order_result is not None:
                    # unpack in case we want to process or store those values
                    (alpaca_order, newStartingPrice, newTargetPrice, newStopLossPrice, trailing_percent, newQuantity) = alpaca_order_result
                    # add it to our 'submitted' list
                    symbols_submitted.append(symbol)
                
                # make sure you sleep a bit to avoid hitting api limit
                time.sleep(1)
                    
            except Exception as ex:
                print('\t Skipping: Exception: {0}\n'.format(ex))

        print('Submitted {0} hedged orders: {1}'.format(len(symbols_submitted), str(symbols_submitted)))