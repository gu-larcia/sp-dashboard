# Stock Performance Dashboard

This project provides a simple command line interface for viewing Robinhood portfolio performance.  Historical account information is pulled directly from a Robinhood account and compared against the S&P 500.  Graphs are displayed with matplotlib and include a basic trend forecast.

## Features

* Fetches historical portfolio data using `robin_stocks`.
* Compares portfolio performance to the S&P 500 using `yfinance`.
* Displays charts for equity history, performance vs S&P 500 and a linear forecast.

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
python dashboard.py
```

A menu will allow you to select different graphs.

## Disclaimer

This example uses unofficial Robinhood APIs via the `robin_stocks` package.  Use at your own risk.
