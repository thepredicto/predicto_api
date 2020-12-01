import enum
import matplotlib.pyplot as plt
import pandas as pd
import requests

class TradeAction(enum.IntEnum):
    Noaction = 0
    Buy = 1
    Sell = 2

class PredictoApiWrapper(object):
    """Api wrapper class for Predicto (https://predic.to)"""
    
    _base_url = 'https://predic.to'

    def __init__(self, apiSessionId):
        self._head = {'Cookie': 'session={0}'.format(apiSessionId)}

    def get_supported_tickers(self):
        """Returns a list of supported tickers
        
        Args:
            return_pandas_df: returns a pandas dataframe if True, json otherwise
        
        Returns:
            json with all the supported tickers
        """
        endpoint = "{0}/stocks/all".format(PredictoApiWrapper._base_url)
        jsn = requests.get(endpoint, headers=self._head).json()
        
        return jsn
    
    def get_forecast(self, ticker, date):
        """Returns the forecast of the selected ticker for selected date
        
        Args:
            ticker: the ticker of the stock
            date: the date of the forecast (YYYY-MM-DD format)
        
        Returns:
            json with retrieved forecast
        """
        endpoint = "{0}/api/forecasting/{1}/{2}/-1".format(PredictoApiWrapper._base_url, ticker, date)
        jsn = requests.get(endpoint, headers=self._head).json()
        
        forecasting_json = jsn[0]['PredictionsJson']
        
        return forecasting_json
    
    def get_trade_pick(self, ticker, date):
        """Returns generated trade pick of the selected ticker for selected date based on that date's forecast
        
        Args:
            ticker: the ticker of the stock
            date: the date of the forecast (YYYY-MM-DD format)
        
        Returns:
            json with retrieved trade pick
        """
        endpoint = "{0}/api/forecasting/tradepicks/{1}/{2}/_,0.0,0".format(PredictoApiWrapper._base_url, ticker, date)
        jsn = requests.get(endpoint, headers=self._head).json()
        
        trade_pick_json = jsn['Recommendations'][0]
        
        return trade_pick_json
            
    def get_model_recent_performance_graph(self, ticker):
        """Returns recent performance GIF url for selected ticker
        
        Args:
            ticker: the ticker of the stock
        
        Returns:
            the gif URL
        """
        endpoint = "{0}/api/history/blobs/{1}".format(PredictoApiWrapper._base_url, ticker)
        jsn = requests.get(endpoint, headers=self._head).json()

        return jsn[0]['ForecastModelGifBlobUrl'].split("?")[0]

    def get_forecast_and_tradepick_info(self, ticker, date, print_it=False):
        """Helper method to retrieve forecast and trade pick for given ticker and date
        
        Args:
            ticker: the ticker of the stock
            date: the date of the forecast (YYYY-MM-DD format)
            print_it: whether to print retrieved info and plot
        
        Returns:
            The forecast json and trade pick json as (forecast_json, trade_pick_json)
        """
        # retrieve forecast and trade pick
        forecast_json = self.get_forecast(ticker, date)
        trade_pick_json = self.get_trade_pick(ticker, date)
        
        if print_it:
            print('Forecast for {0} on {1}'.format(ticker, date))

            # convert to pandas dataframe and plot forecast
            forecast_df = pd.read_json(forecast_json, orient='index')
            forecast_df.Prediction.plot()
            plt.show()

            # print forecast info
            print(forecast_df[['Prediction', 'Uncertainty']])
            print()

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