# predicto_api
Python library for predicto api for financial timeseries forecasting

More info at [https://predic.to](https://predic.to)

## Usage

Start by installing required packages

```
pip install -r predicto_api/requirements.txt
```

To use predicto_api wrapper, you'll need a valid account at https://predic.to, and an `api_session_id` that you can find in your settings page.

```python
from predicto_api_wrapper import PredictoApiWrapper

# retrieve api_session_id from your https://predic.to/settings page
api_session_id = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

# prepare our predicto api wrapper
predicto_api_wrapper = PredictoApiWrapper(api_session_id)

# define the ticker and date we are interested in
ticker = 'TSLA'
date = '2020-11-28'

# get suppported tickers for which daily forecasts are available
tickers_df = predicto_api_wrapper.get_supported_tickers(True)

# get forecast dataframe
forecast_df = predicto_api_wrapper.get_forecast(ticker, date, True)

# get trade pick dataframe based on that forecast (entry, exit, stop-loss price)
trade_pick_df = predicto_api_wrapper.get_trade_pick(ticker, date, True)
```

## Jupyter notebook sample

For detailed usage, check the [example_usage notebook](Notebooks/example_usage.ipynb) in the `Notebooks` folder.
