# predicto_api
Python library for Predicto API.

Predicto generates stock market signals and short-term forecasts daily. Powered by intelligible Deep Learning models, based on News & Options Data.

More info at [https://predic.to](https://predic.to)

## Usage

Start by installing required packages

```
pip install -r predicto_api/requirements.txt
```

To use predicto_api wrapper, you'll need a valid account at https://predic.to, and an `api_key` that you can find in your https://predic.to/account page.

```python
from predicto_api_wrapper import PredictoApiWrapper

# retrieve api_key from your https://predic.to/account page
api_key = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

# prepare our predicto api wrapper
api = PredictoApiWrapper(api_key)
```

## Retrieving Predicto Nasdaq-100 Signals
Predicto Nasdaq Signals are generated daily and are based on the combined forecasting power of hundreds of Deep Learning models.

`Nasdaq Outlook Score` gives you a stock market feeling with a 15-days ahead horizon.

`Nasdaq Forecasted Volatility` is the standard deviation of the forecasted 15-days ahead movements (percentage). 

`Nasdaq Models Uncertainty` is a measurement of how uncertain our models are with current market conditions (percentage). 

For detailed information, please check https://predic.to/outlook and https://predic.to/faq.

For detailed usage, check the [predicto_api_nasdaq_signals.ipynb](Notebooks/predicto_api_nasdaq_signals.ipynb) in the `Notebooks` folder.

```python
# retrieve info for last 20 days
since_date = (datetime.today() - timedelta(days=20)).strftime('%Y-%m-%d')

# get Nasdaq Outlook Score information
outlook_json = api.get_nasdaq_outlook_score_since(since_date)

# get Nasdaq Forecasted Volatility information
volatility_json = api.get_nasdaq_forecasted_volatility_since(since_date)

# get Models Uncertainty information
uncertainty_json = api.get_nasdaq_models_uncertainty_since(since_date)
```

## Retrieving AutoTrader's stock forecasts and trade picks
For detailed usage, check the [predicto_api_example_usage.ipynb](Notebooks/predicto_api_example_usage.ipynb) in the `Notebooks` folder.

```python
import pandas as pd

# get suppported tickers for which daily forecasts are available
tickers_json = api.get_supported_tickers()
tickers_df = pd.DataFrame(tickers_json)

# define the ticker and date we are interested in (use yesterday's date to get latest)
ticker = 'TSLA'
date = '2020-11-28'

# get forecast dataframe
forecast_json = api.get_forecast(ticker, date)
forecast_df = pd.read_json(forecast_json, orient='index')

# get trade pick based on that forecast (entry, exit, stop-loss price)
trade_pick_json = api.get_trade_pick(ticker, date)
```

## Using Predicto with Alpaca to setup daily AutoTrader
Make sure you understand the risks if you are using real money!
We recommend that you start by experimenting with an Alpaca Paper acccount.

```python
from predicto_api_wrapper import PredictoApiWrapper, TradeAction, TradeOrderType
from alpaca_api_wrapper import AlpacaApiWrapper

# initialize alpaca api wrapper
alpaca_api_endpoint = 'https://paper-api.alpaca.markets' # use paper money endpoint for now (test env)
alpaca_api_key_id = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
alpaca_api_secret_key = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

alpaca_wrapper = AlpacaApiWrapper(alpaca_api_endpoint, alpaca_api_key_id, alpaca_api_secret_key)

# initialize predicto api wrapper
predicto_api_key = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
api = PredictoApiWrapper(predicto_api_key)
api.set_alpaca_api_wrapper(alpaca_wrapper)

# Option 1:
#   Execute Predicto AutoTrader
#   You can schedule this script to run daily just after market open (9.31am E.T.).
#   It will submit last day's Trade Picks matching your criteria.
#   Note: Make sure you understand the risks if you are using real money!
api.submit_latest_trade_picks(
        abs_change_pct_threshold = 0.02,
        actions = [int(TradeAction.Buy), int(TradeAction.Sell)],
        average_uncertainty = 0.15,
        model_avg_roi = 0.0,
        symbols = None,
        investment_per_trade=1000,
        trade_order_type=TradeOrderType.Bracket,
        stoploss_fixed_pct=None)

# Option 2:
#   Execute Predicto AutoTrader using "My Picks" as you picked them in Predicto website!
#   Manually pick them every night at https://predic.to/autotrader
#   You can schedule this script to run daily just after market open (9.31am E.T.)
#   It will submit last day's "My Picks"
#   Note: Make sure you understand the risks if you are using real money!
api.submit_my_latest_trade_picks(
        investment_per_trade=1000,
        trade_order_type=TradeOrderType.Bracket)
```

## AutoTrader daily script

Sample AutoTrader using Predicto Forecasts with Alpaca can be found in [autotrader_daily.py](samples/autotrader_daily.py) or [autotrader_my_picks_daily.py](samples/autotrader_my_picks_daily.py) in the `samples` folder.

## Jupyter Notebook For Predicto API interactions

For detailed usage of PredictoApiWrapper, check the [predicto_api_example_usage.ipynb](Notebooks/predicto_api_example_usage.ipynb) in the `Notebooks` folder.

## Jupyter Notebook for AutoTrader using Alpaca API

You can use latest Forecasts and Trade Picks generated by Predicto with Alpaca API. To see how, check the [predicto_autotrader_example.ipynb](Notebooks/predicto_autotrader_example.ipynb) in the `Notebooks` folder.

More info on Alpaca API and for documentation, check https://alpaca.markets/.

## More info

For more information on how our Deep Learning forecasts are generated, follow us on https://medium.com/@thepredicto

## Disclaimer

Please read our disclaimer carefully: https://predic.to/disclaimer
