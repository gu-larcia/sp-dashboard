# Stock Performance Dashboard

This project provides a simple command line interface for viewing Robinhood portfolio performance. Historical data is fetched directly from Robinhood's API and compared against the S&P 500 using `yfinance`. Charts are rendered with matplotlib and include a basic forecast.

## Features

* Connects to Robinhood using HTTPS requests (no `robin_stocks` dependency).
* Asynchronously downloads portfolio history and benchmark data.
* Caches recent portfolio responses to reduce API calls.
* Command line interface supports non-interactive usage and saving charts to files.

## Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Usage

Set your Robinhood credentials in environment variables or enter them when prompted:

```bash
export RH_USERNAME="your_username"
export RH_PASSWORD="your_password"
# optional
export RH_MFA="123456"
```

Run the dashboard:

```bash
python dashboard.py interactive
```

You can also run a specific graph directly from the command line. For example:

```bash
python dashboard.py portfolio --span year --interval day -o myplot.png
```

Use `--refresh` to bypass the local cache when you want the latest data.

## Disclaimer

This tool uses Robinhood's public endpoints. Usage may be subject to Robinhood's terms and rate limits.
