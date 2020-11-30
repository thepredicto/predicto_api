import requests
import pandas as pd
import matplotlib.pyplot as plt
import enum

class TradeAction(enum.IntEnum):
    Noaction = 0
    Buy = 1
    Sell = 2

class PredictoApiWrapper(object):
    """Api wrapper class for Predicto (https://predic.to)"""
    
    _base_url = 'https://predic.to'

    def __init__(self, apiSessionId):
        self._head = {'Cookie': 'session={0}'.format(apiSessionId)}

    def get_supported_tickers(self, return_pandas_df=False):
        """Returns a list of supported tickers
        
        Args:
            return_pandas_df: returns a pandas dataframe if True, json otherwise
        
        Returns:
            A pandas dataframe with all the supported tickers
        """
        endpoint = "{0}/stocks/all".format(PredictoApiWrapper._base_url)
        jsn = requests.get(endpoint, headers=self._head).json()
        
        return jsn if not return_pandas_df else pd.DataFrame(jsn)
    
    def get_forecast(self, ticker, date, return_pandas_df=False):
        """Returns the forecast of the selected ticker for selected date
        
        Args:
            ticker: the ticker of the stock
            date: the date of the forecast (YYYY-MM-DD format)
            return_pandas_df: returns a pandas dataframe if True, json otherwise
        
        Returns:
            A pandas dataframe or json with retrieved forecast
        """
        endpoint = "{0}/api/forecasting/{1}/{2}/-1".format(PredictoApiWrapper._base_url, ticker, date)
        jsn = requests.get(endpoint, headers=self._head).json()
        
        forecasting_json = jsn[0]['PredictionsJson']
        
        if return_pandas_df:
             return pd.read_json(forecasting_json, orient='index')
        
        return forecasting_json
    
    def get_trade_pick(self, ticker, date, return_pandas_df=False):
        """Returns generated trade pick of the selected ticker for selected date based on that date's forecast
        
        Args:
            ticker: the ticker of the stock
            date: the date of the forecast (YYYY-MM-DD format)
            return_pandas_df: returns a pandas dataframe if True, json otherwise
        
        Returns:
            A pandas dataframe or json with retrieved trade pick
        """
        endpoint = "{0}/api/forecasting/tradepicks/{1}/{2}/_,0.0,0".format(PredictoApiWrapper._base_url, ticker, date)
        jsn = requests.get(endpoint, headers=self._head).json()
        
        trade_pick_json = jsn['Recommendations'][0]
        
        if return_pandas_df:
            return pd.DataFrame(list(trade_pick_json.items()), columns=['Name', 'Value']).set_index('Name')
        
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
        