"""
Swing high/low detection — the building block that triangle, double
top/bottom and head-and-shoulders detectors are built on.

A bar at position i is a swing high if its High is the maximum within the
window [i-order, i+order], and a swing low if its Low is the minimum within
that same window. `order` controls how "zoomed out" the swings are: a
bigger order means fewer, more significant swing points.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class SwingPoint:
    pos: int              # integer position in the dataframe
    timestamp: pd.Timestamp
    price: float
    kind: str              # "high" or "low"


def find_swing_highs(df: pd.DataFrame, order: int = 3) -> list[SwingPoint]:
    highs = df["High"].to_numpy()
    n = len(highs)
    out = []
    for i in range(order, n - order):
        window = highs[i - order : i + order + 1]
        if highs[i] == window.max() and np.sum(window == highs[i]) == 1:
            out.append(SwingPoint(i, df.index[i], float(highs[i]), "high"))
    return out


def find_swing_lows(df: pd.DataFrame, order: int = 3) -> list[SwingPoint]:
    lows = df["Low"].to_numpy()
    n = len(lows)
    out = []
    for i in range(order, n - order):
        window = lows[i - order : i + order + 1]
        if lows[i] == window.min() and np.sum(window == lows[i]) == 1:
            out.append(SwingPoint(i, df.index[i], float(lows[i]), "low"))
    return out


def fit_line(points: list[SwingPoint]) -> tuple[float, float]:
    """Least-squares line through (pos, price) pairs. Returns (slope, intercept)
    such that price ~= slope * pos + intercept."""
    xs = np.array([p.pos for p in points], dtype=float)
    ys = np.array([p.price for p in points], dtype=float)
    slope, intercept = np.polyfit(xs, ys, 1)
    return float(slope), float(intercept)
