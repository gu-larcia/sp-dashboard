import os
import getpass
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from robin_stocks import robinhood as rh


def login():
    """Login to Robinhood using environment variables or interactive prompts."""
    username = os.getenv("RH_USERNAME")
    password = os.getenv("RH_PASSWORD")
    if username is None:
        username = input("Robinhood username: ")
    if password is None:
        password = getpass.getpass("Robinhood password: ")
    mfa = os.getenv("RH_MFA")
    if mfa is None:
        mfa_input = input("MFA code (press enter if not required): ")
        mfa = mfa_input if mfa_input else None
    rh.login(username=username, password=password, mfa_code=mfa)


def portfolio_history(span="year", interval="day"):
    """Return portfolio equity history as a DataFrame."""
    data = rh.account.get_historical_portfolio(span=span, interval=interval)
    df = pd.DataFrame(data)
    df["begins_at"] = pd.to_datetime(df["begins_at"])
    df.set_index("begins_at", inplace=True)
    df["equity"] = df["equity"].astype(float)
    return df


def sp500_history(start, end):
    """Download S&P500 historical data for comparison."""
    sp = yf.download("^GSPC", start=start, end=end, progress=False)
    sp.index = sp.index.tz_localize(None)
    return sp


def show_portfolio(span="year", interval="day"):
    df = portfolio_history(span=span, interval=interval)
    plt.figure()
    df["equity"].plot()
    plt.title("Portfolio Value Over Time")
    plt.xlabel("Date")
    plt.ylabel("Equity ($)")
    plt.tight_layout()
    plt.show()


def show_compare(span="year", interval="day"):
    df = portfolio_history(span=span, interval=interval)
    sp = sp500_history(df.index[0].date(), df.index[-1].date())
    norm_port = df["equity"] / df["equity"].iloc[0] * 100
    norm_sp = sp["Adj Close"] / sp["Adj Close"].iloc[0] * 100
    plt.figure()
    plt.plot(norm_port.index, norm_port, label="Portfolio")
    plt.plot(norm_sp.index, norm_sp, label="S&P500")
    plt.legend()
    plt.title("Performance vs S&P500")
    plt.ylabel("Performance (Indexed)")
    plt.tight_layout()
    plt.show()


def show_forecast(span="year", interval="day"):
    df = portfolio_history(span=span, interval=interval)
    y = df["equity"].values
    x = np.arange(len(y))
    coeffs = np.polyfit(x, y, 1)
    trend = coeffs[0] * x + coeffs[1]
    plt.figure()
    plt.plot(df.index, y, label="Actual")
    plt.plot(df.index, trend, label="Linear Trend", linestyle="--")
    plt.legend()
    plt.title("Portfolio Forecast")
    plt.tight_layout()
    plt.show()


def menu():
    options = {
        "1": ("Portfolio value over time", show_portfolio),
        "2": ("Performance vs S&P500", show_compare),
        "3": ("Forecast", show_forecast),
        "4": ("Exit", None),
    }
    while True:
        print("\nStock Performance Dashboard")
        for key, (desc, _) in options.items():
            print(f"{key}. {desc}")
        choice = input("Select an option: ").strip()
        if choice == "4":
            break
        _, action = options.get(choice, (None, None))
        if action:
            action()
        else:
            print("Invalid choice. Try again.")


if __name__ == "__main__":
    try:
        login()
    except Exception as exc:
        print(f"Failed to login: {exc}")
        sys.exit(1)
    menu()
