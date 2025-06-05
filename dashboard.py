import sys
import argparse
import asyncio
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf

from robinhood_api import login, portfolio_history_df

async def sp500_history(start, end):
    """Asynchronously download S&P500 historical data."""
    sp = await asyncio.to_thread(
        yf.download,
        "^GSPC",
        start=start,
        end=end,
        progress=False,
    )
    sp.index = sp.index.tz_localize(None)
    return sp

async def async_show_portfolio(span="year", interval="day", output=None, refresh=False):
    df = await portfolio_history_df(span=span, interval=interval, refresh=refresh)
    fig, ax = plt.subplots()
    df["equity"].plot(ax=ax)
    ax.set_title("Portfolio Value Over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity ($)")
    fig.tight_layout()
    if output:
        fig.savefig(output)
    else:
        plt.show()

async def async_show_compare(span="year", interval="day", output=None, refresh=False):
    df_task = portfolio_history_df(span=span, interval=interval, refresh=refresh)
    df = await df_task
    sp_task = sp500_history(df.index[0].date(), df.index[-1].date())
    sp = await sp_task
    norm_port = df["equity"] / df["equity"].iloc[0] * 100
    norm_sp = sp["Adj Close"] / sp["Adj Close"].iloc[0] * 100
    fig, ax = plt.subplots()
    ax.plot(norm_port.index, norm_port, label="Portfolio")
    ax.plot(norm_sp.index, norm_sp, label="S&P500")
    ax.legend()
    ax.set_title("Performance vs S&P500")
    ax.set_ylabel("Performance (Indexed)")
    fig.tight_layout()
    if output:
        fig.savefig(output)
    else:
        plt.show()

async def async_show_forecast(span="year", interval="day", output=None, refresh=False):
    df = await portfolio_history_df(span=span, interval=interval, refresh=refresh)
    y = df["equity"].values
    x = np.arange(len(y))
    coeffs = np.polyfit(x, y, 1)
    trend = coeffs[0] * x + coeffs[1]
    fig, ax = plt.subplots()
    ax.plot(df.index, y, label="Actual")
    ax.plot(df.index, trend, label="Linear Trend", linestyle="--")
    ax.legend()
    ax.set_title("Portfolio Forecast")
    fig.tight_layout()
    if output:
        fig.savefig(output)
    else:
        plt.show()


def show_portfolio(span="year", interval="day", output=None, refresh=False):
    asyncio.run(async_show_portfolio(span, interval, output, refresh))


def show_compare(span="year", interval="day", output=None, refresh=False):
    asyncio.run(async_show_compare(span, interval, output, refresh))


def show_forecast(span="year", interval="day", output=None, refresh=False):
    asyncio.run(async_show_forecast(span, interval, output, refresh))


def menu(refresh=False):
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
            action(refresh=refresh)
        else:
            print("Invalid choice. Try again.")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Stock Performance Dashboard")
    sub = parser.add_subparsers(dest="command")

    common = {
        "span": dict(default="year", help="Data span e.g. day, week, year"),
        "interval": dict(default="day", help="Data interval"),
    }

    p = sub.add_parser("portfolio", help="Show portfolio value over time")
    p.add_argument("--span", **common["span"])
    p.add_argument("--interval", **common["interval"])
    p.add_argument("-o", "--output", help="Save plot to file")

    c = sub.add_parser("compare", help="Compare portfolio vs S&P500")
    c.add_argument("--span", **common["span"])
    c.add_argument("--interval", **common["interval"])
    c.add_argument("-o", "--output", help="Save plot to file")

    f = sub.add_parser("forecast", help="Show portfolio forecast")
    f.add_argument("--span", **common["span"])
    f.add_argument("--interval", **common["interval"])
    f.add_argument("-o", "--output", help="Save plot to file")

    sub.add_parser("interactive", help="Run interactive menu")

    parser.add_argument("--no-login", action="store_true", help="Skip login")
    parser.add_argument("--refresh", action="store_true", help="Bypass local cache")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if not args.no_login:
        try:
            asyncio.run(login())
        except Exception as exc:
            print(f"Failed to login: {exc}")
            sys.exit(1)

    if args.command == "portfolio":
        show_portfolio(args.span, args.interval, args.output, args.refresh)
    elif args.command == "compare":
        show_compare(args.span, args.interval, args.output, args.refresh)
    elif args.command == "forecast":
        show_forecast(args.span, args.interval, args.output, args.refresh)
    else:
        menu(refresh=args.refresh)
