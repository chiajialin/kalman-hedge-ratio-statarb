"""
Fetch daily OHLCV data for ES, NQ, YM, and RTY continuous front-month futures from
Yahoo Finance.

Calls Yahoo's chart API directly via requests rather than through yfinance, due to a
TLS certificate conflict between yfinance's bundled curl_cffi and network-level HTTPS
inspection on this machine.
"""

import time
import requests
import pandas as pd

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
HEADERS = {"User-Agent": "Mozilla/5.0"}

START_DATE = "2020-01-01"
END_DATE = "2026-06-26"


def fetch_daily(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Fetch daily OHLCV bars for a Yahoo Finance ticker over a date range.

    Args:
        ticker: Yahoo Finance ticker symbol (e.g. 'ES=F').
        start:  Start date string in YYYY-MM-DD format (inclusive).
        end:    End date string in YYYY-MM-DD format (exclusive).

    Returns:
        DataFrame with columns [open, high, low, close, volume] indexed by date.
    """
    params = {
        "period1": int(pd.Timestamp(start).timestamp()),
        "period2": int(pd.Timestamp(end).timestamp()),
        "interval": "1d",
    }
    response = requests.get(
        CHART_URL.format(ticker=ticker), headers=HEADERS, params=params, timeout=10
    )
    response.raise_for_status()

    result = response.json()["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]

    df = pd.DataFrame(
        {
            "open": quote["open"],
            "high": quote["high"],
            "low": quote["low"],
            "close": quote["close"],
            "volume": quote["volume"],
        },
        index=pd.to_datetime(result["timestamp"], unit="s"),
    )
    df.index.name = "date"
    return df.dropna()


if __name__ == "__main__":
    print(f"Fetching ES daily data ({START_DATE} to {END_DATE})...")
    es = fetch_daily("ES=F", START_DATE, END_DATE)
    time.sleep(1)

    print(f"Fetching NQ daily data ({START_DATE} to {END_DATE})...")
    nq = fetch_daily("NQ=F", START_DATE, END_DATE)
    time.sleep(1)

    print(f"Fetching YM daily data ({START_DATE} to {END_DATE})...")
    ym = fetch_daily("YM=F", START_DATE, END_DATE)
    time.sleep(1)

    print(f"Fetching RTY daily data ({START_DATE} to {END_DATE})...")
    rty = fetch_daily("RTY=F", START_DATE, END_DATE)
    time.sleep(1)

    es.to_csv("data/raw/es_daily.csv")
    nq.to_csv("data/raw/nq_daily.csv")
    ym.to_csv("data/raw/ym_daily.csv")
    rty.to_csv("data/raw/rty_daily.csv")
    print("Saved to data/raw/es_daily.csv, data/raw/nq_daily.csv, data/raw/ym_daily.csv, and data/raw/rty_daily.csv")

    print(f"\nES: {es.shape[0]} rows | {es.index.min().date()} to {es.index.max().date()}")
    print(es.head())
    print(f"\nNQ: {nq.shape[0]} rows | {nq.index.min().date()} to {nq.index.max().date()}")
    print(nq.head())
    print(f"\nYM: {ym.shape[0]} rows | {ym.index.min().date()} to {ym.index.max().date()}")
    print(ym.head())
    print(f"\nRTY: {rty.shape[0]} rows | {rty.index.min().date()} to {rty.index.max().date()}")
    print(rty.head())
