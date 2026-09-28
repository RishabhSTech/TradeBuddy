"""
Symbol map for the three indices we care about.

Yahoo Finance tickers are the default free data source (data.py). If you
later wire in a broker feed (Kite/Angel One/Dhan/Upstox WebSocket) instead,
map their instrument tokens here too, so the rest of the codebase never has
to care where a bar came from.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class IndexSpec:
    key: str            # short internal key used everywhere in this app
    name: str            # human-readable name, used in alerts
    yfinance_ticker: str  # Yahoo Finance ticker
    tick_size: float     # approx minimum meaningful move, used for rounding


INDICES = {
    "NIFTY": IndexSpec("NIFTY", "Nifty 50", "^NSEI", 0.05),
    "BANKNIFTY": IndexSpec("BANKNIFTY", "Bank Nifty", "^NSEBANK", 0.05),
    "SENSEX": IndexSpec("SENSEX", "Sensex", "^BSESN", 0.1),
}

DEFAULT_KEYS = list(INDICES.keys())
