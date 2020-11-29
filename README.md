# predicto_api
Python library for predicto api for financial timeseries forecasting

More info at [https://predic.to](https://predic.to)

## Usage

To use predicto_api wrapper, you'll need a valid account at https://predic.to, and an `api_session_id` that you can find in your settings page.

```python
from predicto_api_wrapper import PredictoApiWrapper

# retrieve api_session_id from your https://predic.to/settings page
api_session_id = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

ticker = 'TSLA'
date = '2020-11-28'

api_wrapper = PredictoApiWrapper(api_session_id)

tickers_df = api_wrapper.get_supported_tickers(True)
forecast_df = api_wrapper.get_forecast(ticker, date, True)
trade_pick_df = api_wrapper.get_trade_pick(ticker, date, True)
```

## Jupyter notebook sample

For detailed usage, check the [example_usage notebook](Notebooks/example_usage.ipynb) in the `Notebooks` folder.
