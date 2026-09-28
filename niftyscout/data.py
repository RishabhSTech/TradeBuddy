"""
Data providers.

The rest of the app only depends on `DataProvider.get_bars(...)` returning a
pandas DataFrame with columns [Open, High, Low, Close, Volume] and a
DatetimeIndex sorted ascending. Swap YFinanceProvider for a broker
WebSocket-backed provider later without touching detectors or the scanner.
"""

from __future__ import annotations

import abc
import datetime as dt
from zoneinfo import ZoneInfo

import pandas as pd

from .symbols import INDICES

IST = ZoneInfo("Asia/Kolkata")

# NSE/BSE cash market hours (equity index trading window)
MARKET_OPEN = dt.time(9, 15)
MARKET_CLOSE = dt.time(15, 30)


def now_ist() -> dt.datetime:
    return dt.datetime.now(tz=IST)


def is_market_open(moment: dt.datetime | None = None) -> bool:
    """Rough check: NSE/BSE trading window, Mon-Fri. Does not account for
    exchange holidays -- plug in a holiday calendar if you need that."""
    moment = moment or now_ist()
    if moment.weekday() >= 5:  # Sat/Sun
        return False
    t = moment.timetz()
    return MARKET_OPEN <= t.replace(tzinfo=None) <= MARKET_CLOSE


class DataProvider(abc.ABC):
    @abc.abstractmethod
    def get_bars(self, index_key: str, interval: str, lookback: str) -> pd.DataFrame:
        """Return OHLCV bars for one index.

        interval: pandas/yfinance-style string, e.g. "5m", "15m", "1d"
        lookback: yfinance-style period string, e.g. "5d", "60d", "2y"
        """


class YFinanceProvider(DataProvider):
    """Free, delayed (typically 15-20 min) data. Good enough for spotting a
    pattern and getting a heads-up; NOT a substitute for your broker's live
    feed if you plan to act within seconds of a breakout.

    Requires network access to Yahoo Finance, which this sandbox does not
    have (proxy allowlist), but works from an ordinary machine/server.
    """

    def __init__(self):
        import yfinance as yf  # imported lazily so tests don't need it

        self._yf = yf

    def get_bars(self, index_key: str, interval: str = "15m", lookback: str = "5d") -> pd.DataFrame:
        spec = INDICES[index_key]
        df = self._yf.download(
            spec.yfinance_ticker,
            period=lookback,
            interval=interval,
            progress=False,
            auto_adjust=False,
        )
        if df.empty:
            return df
        # yfinance sometimes returns a MultiIndex column set for a single ticker
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC").tz_convert(IST)
        else:
            df.index = df.index.tz_convert(IST)
        return df


class CSVProvider(DataProvider):
    """Reads bars from a local CSV per index (columns: Date/Datetime, Open,
    High, Low, Close, Volume). Useful for replay/backtesting against a
    bhavcopy-derived file or an export from your broker's charting tool."""

    def __init__(self, paths: dict[str, str]):
        self.paths = paths

    def get_bars(self, index_key: str, interval: str = "15m", lookback: str = "5d") -> pd.DataFrame:
        path = self.paths[index_key]
        df = pd.read_csv(path)
        date_col = "Datetime" if "Datetime" in df.columns else "Date"
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col).sort_index()
        if df.index.tz is None:
            df.index = df.index.tz_localize(IST)
        return df[["Open", "High", "Low", "Close", "Volume"]]
