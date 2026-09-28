"""
Builds small synthetic OHLCV series with a known pattern baked in, so the
detectors can be tested deterministically without needing live/network data.

Patterns are built as an explicit zigzag through anchor prices (each anchor
becomes an unambiguous swing high/low), then a breakout leg is appended.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _to_df(closes: np.ndarray, wobble: float = 0.15, start="2026-01-01 09:15", freq="15min") -> pd.DataFrame:
    n = len(closes)
    idx = pd.date_range(start=start, periods=n, freq=freq, tz="Asia/Kolkata")
    highs = closes + wobble
    lows = closes - wobble
    opens = np.roll(closes, 1)
    opens[0] = closes[0]
    vol = np.full(n, 100000)
    return pd.DataFrame(
        {"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": vol}, index=idx
    )


def _zigzag(anchors: list[float], bars_per_leg: int = 4) -> np.ndarray:
    """Linearly interpolate between successive anchor prices, `bars_per_leg`
    bars per leg, without duplicating the shared point at each junction (so
    every anchor is a clean, unique local extremum)."""
    legs = []
    for i in range(len(anchors) - 1):
        leg = np.linspace(anchors[i], anchors[i + 1], bars_per_leg, endpoint=True)
        legs.append(leg if i == 0 else leg[1:])
    return np.concatenate(legs)


def make_range_then_breakout(n_range: int = 30, base: float = 100.0, band: float = 0.5, breakout: float = 3.0) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    range_part = base + rng.uniform(-band, band, size=n_range)
    breakout_part = np.array([base + band + breakout])
    closes = np.concatenate([range_part, breakout_part])
    return _to_df(closes)


def make_ascending_triangle(resistance: float = 105.0, base_low: float = 100.0, taps: int = 5) -> pd.DataFrame:
    """Flat resistance, rising swing lows, then a clean breakout above
    resistance. Anchors alternate: low, resistance, higher low, resistance, ..."""
    anchors = [base_low]
    for k in range(taps):
        anchors.append(resistance)
        anchors.append(base_low + (resistance - base_low) * 0.15 * (k + 1))
    body = _zigzag(anchors, bars_per_leg=4)
    breakout = np.linspace(body[-1], resistance + 2.5, 3)[1:]
    closes = np.concatenate([body, breakout])
    return _to_df(closes, wobble=0.1)


def make_double_top(base: float = 100.0, peak: float = 110.0, trough: float = 104.0) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    lead_in = base + rng.uniform(-0.3, 0.3, size=8)
    anchors = [lead_in[-1], peak, trough, peak - 0.2]
    body = _zigzag(anchors, bars_per_leg=6)
    breakdown = np.linspace(body[-1], trough - 3, 5)[1:]
    closes = np.concatenate([lead_in, body[1:], breakdown])
    return _to_df(closes, wobble=0.12)


def make_double_bottom(base: float = 100.0, dip: float = 90.0, peak: float = 96.0) -> pd.DataFrame:
    rng = np.random.default_rng(9)
    lead_in = base + rng.uniform(-0.3, 0.3, size=8)
    anchors = [lead_in[-1], dip, peak, dip + 0.2]
    body = _zigzag(anchors, bars_per_leg=6)
    breakout = np.linspace(body[-1], peak + 3, 5)[1:]
    closes = np.concatenate([lead_in, body[1:], breakout])
    return _to_df(closes, wobble=0.12)


def make_head_and_shoulders(base: float = 100.0, shoulder: float = 108.0, head: float = 115.0, neck: float = 102.0) -> pd.DataFrame:
    rng = np.random.default_rng(11)
    lead_in = base + rng.uniform(-0.3, 0.3, size=6)
    anchors = [lead_in[-1], shoulder, neck, head, neck + 0.3, shoulder - 0.3, neck - 0.1]
    body = _zigzag(anchors, bars_per_leg=5)
    breakdown = np.linspace(body[-1], neck - 4, 6)[1:]
    closes = np.concatenate([lead_in, body[1:], breakdown])
    return _to_df(closes, wobble=0.12)


def make_opening_range_breakout(base: float = 100.0, or_minutes_bars: int = 3, breakout: float = 2.0) -> pd.DataFrame:
    """5-minute bars: first 3 bars form the opening range, then a clean
    breakout above it, all within a single trading day."""
    rng = np.random.default_rng(3)
    or_part = base + rng.uniform(-0.2, 0.2, size=or_minutes_bars)
    drift = np.linspace(base, base + breakout + 0.5, 5)
    closes = np.concatenate([or_part, drift])
    idx = pd.date_range("2026-06-01 09:15", periods=len(closes), freq="5min", tz="Asia/Kolkata")
    highs = closes + 0.1
    lows = closes - 0.1
    opens = np.roll(closes, 1)
    opens[0] = closes[0]
    vol = np.full(len(closes), 50000)
    return pd.DataFrame(
        {"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": vol}, index=idx
    )
