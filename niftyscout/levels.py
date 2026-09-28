"""
Turns a Signal's own geometry (the level it broke, the pattern's height) plus
volatility (ATR) and volume-profile structure into a concrete entry/stop/
target plan -- what a discretionary technical analyst would sketch on the
chart, computed instead of eyeballed.

This is deliberately NOT trading advice: every number here is a transparent
function of the pattern's own structure, and `basis` always says exactly
which inputs produced it. See `analyst.py` for the plain-English narration,
which repeats this same "structure, not advice" framing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pandas as pd

from .swings import find_swing_highs, find_swing_lows
from .volume_profile import VolumeProfile, nearest_level

if TYPE_CHECKING:
    from .indicators import IndicatorSnapshot
    from .patterns import Signal


@dataclass
class TradePlan:
    entry: float
    stop: float
    target1: float
    target2: float | None
    risk_per_unit: float
    reward_to_target1: float
    r_multiple_1: float
    r_multiple_2: float | None
    method: str
    basis: list[str] = field(default_factory=list)


def _round_tick(price: float, tick_size: float) -> float:
    if tick_size <= 0:
        return price
    return round(round(price / tick_size) * tick_size, 6)


def _swing_stop(df: pd.DataFrame, level: float, bullish: bool, swing_order: int = 3) -> float | None:
    """Fallback stop when ATR isn't available yet (early bars in a fresh
    window): the nearest opposing swing point beyond the broken level."""
    if bullish:
        lows = find_swing_lows(df, order=swing_order)
        candidates = [p.price for p in lows if p.price < level]
        return max(candidates) if candidates else None
    highs = find_swing_highs(df, order=swing_order)
    candidates = [p.price for p in highs if p.price > level]
    return min(candidates) if candidates else None


def _swing_target(df: pd.DataFrame, beyond: float, bullish: bool, swing_order: int = 3) -> float | None:
    if bullish:
        highs = find_swing_highs(df, order=swing_order)
        candidates = [p.price for p in highs if p.price > beyond]
        return min(candidates) if candidates else None
    lows = find_swing_lows(df, order=swing_order)
    candidates = [p.price for p in lows if p.price < beyond]
    return max(candidates) if candidates else None


def build_trade_plan(
    signal: "Signal",
    df: pd.DataFrame,
    indicators: "IndicatorSnapshot | None",
    volume_profile: VolumeProfile | None = None,
    atr_stop_mult: float = 0.5,
    measured_move_mult: float = 1.0,
    tick_size: float = 0.05,
) -> TradePlan | None:
    """Returns `None` (never a fabricated number) when there isn't enough
    structure to place a sensible stop -- e.g. ATR hasn't warmed up yet and
    there's no opposing swing point in the window."""
    bullish = signal.direction == "bullish"
    entry = signal.breakout_price
    basis: list[str] = []

    atr_value = indicators.atr14 if indicators is not None else None
    stop: float | None = None
    method = ""
    if atr_value is not None and atr_value > 0:
        stop = signal.level - atr_value * atr_stop_mult if bullish else signal.level + atr_value * atr_stop_mult
        basis.append(f"stop = {atr_stop_mult}x ATR({atr_value:.2f}) beyond the broken level")
        method = "atr_stop"
    else:
        stop = _swing_stop(df, signal.level, bullish)
        if stop is not None:
            basis.append("stop = nearest opposing swing point (ATR not yet available)")
            method = "swing_stop"

    if stop is None:
        return None

    pattern_height = getattr(signal, "pattern_height", None)
    if pattern_height and pattern_height > 0:
        basis.append("target1 = measured-move projection of the pattern's own height")
    else:
        pattern_height = abs(entry - stop)
        basis.append("target1 = entry-to-stop distance (pattern height unavailable)")
    method += "+measured_move"

    target1 = entry + pattern_height * measured_move_mult if bullish else entry - pattern_height * measured_move_mult

    target2: float | None = None
    if volume_profile is not None:
        target2 = nearest_level(volume_profile, target1, signal.direction)
        if target2 is not None:
            basis.append("target2 = nearest volume-profile level beyond target1")
    if target2 is None:
        target2 = _swing_target(df, target1, bullish)
        if target2 is not None:
            basis.append("target2 = nearest swing point beyond target1")

    entry_r = _round_tick(entry, tick_size)
    stop_r = _round_tick(stop, tick_size)
    target1_r = _round_tick(target1, tick_size)
    target2_r = _round_tick(target2, tick_size) if target2 is not None else None

    risk = abs(entry_r - stop_r)
    if risk <= 0:
        return None
    reward1 = abs(target1_r - entry_r)
    r1 = reward1 / risk
    r2 = abs(target2_r - entry_r) / risk if target2_r is not None else None

    return TradePlan(
        entry=entry_r,
        stop=stop_r,
        target1=target1_r,
        target2=target2_r,
        risk_per_unit=round(risk, 4),
        reward_to_target1=round(reward1, 4),
        r_multiple_1=round(r1, 2),
        r_multiple_2=round(r2, 2) if r2 is not None else None,
        method=method,
        basis=basis,
    )
