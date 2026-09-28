"""
Pattern-breakout detectors.

Every detector takes a bars DataFrame (Open/High/Low/Close/Volume, ascending
DatetimeIndex) plus tunable parameters, and returns a list of Signal objects
for breakouts found in that data. Detectors look at the WHOLE frame passed
to them (useful for replay/backtest); the scanner calls them repeatedly on a
rolling window and only cares about signals on the most recent bar(s).

Nothing here places or sizes a trade. A Signal just means: this pattern
broke out here, at this price, at this confidence. What you do with it is
on you.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .swings import find_swing_highs, find_swing_lows, fit_line


@dataclass
class Signal:
    pattern: str
    direction: str          # "bullish" or "bearish"
    timestamp: pd.Timestamp
    breakout_price: float
    level: float             # the level/line that was broken
    confidence: float        # 0.0-1.0 heuristic, not a probability
    note: str
    index_key: str = ""
    interval: str = ""

    def headline(self) -> str:
        arrow = "↑" if self.direction == "bullish" else "↓"
        return (
            f"{arrow} {self.index_key} {self.pattern} ({self.direction}) @ "
            f"{self.breakout_price:.2f} — {self.note}"
        )


# ---------------------------------------------------------------------------
# 1. Range / support-resistance breakout
# ---------------------------------------------------------------------------

def detect_range_breakout(
    df: pd.DataFrame,
    lookback: int = 20,
    max_range_pct: float = 0.012,
    confirm_pct: float = 0.0008,
) -> list[Signal]:
    """Flags a breakout out of a tight consolidation range.

    A window of `lookback` bars (excluding the breakout bar itself) is
    treated as a "range" if (high-low)/avg_close over that window is under
    max_range_pct. If the next bar's close clears the range high/low by
    confirm_pct, that's a breakout.
    """
    out: list[Signal] = []
    n = len(df)
    if n < lookback + 1:
        return out

    highs = df["High"].to_numpy()
    lows = df["Low"].to_numpy()
    closes = df["Close"].to_numpy()

    for i in range(lookback, n):
        window_hi = highs[i - lookback : i]
        window_lo = lows[i - lookback : i]
        range_high = window_hi.max()
        range_low = window_lo.min()
        avg_close = closes[i - lookback : i].mean()
        if avg_close <= 0:
            continue
        range_pct = (range_high - range_low) / avg_close
        if range_pct > max_range_pct:
            continue

        close = closes[i]
        if close > range_high * (1 + confirm_pct):
            confidence = min(1.0, 0.5 + (max_range_pct - range_pct) * 20)
            out.append(
                Signal(
                    pattern="Range breakout",
                    direction="bullish",
                    timestamp=df.index[i],
                    breakout_price=float(close),
                    level=float(range_high),
                    confidence=round(confidence, 2),
                    note=(
                        f"broke above {lookback}-bar range top "
                        f"{range_high:.2f} (range was {range_pct*100:.2f}% wide)"
                    ),
                )
            )
        elif close < range_low * (1 - confirm_pct):
            confidence = min(1.0, 0.5 + (max_range_pct - range_pct) * 20)
            out.append(
                Signal(
                    pattern="Range breakdown",
                    direction="bearish",
                    timestamp=df.index[i],
                    breakout_price=float(close),
                    level=float(range_low),
                    confidence=round(confidence, 2),
                    note=(
                        f"broke below {lookback}-bar range bottom "
                        f"{range_low:.2f} (range was {range_pct*100:.2f}% wide)"
                    ),
                )
            )
    return out


# ---------------------------------------------------------------------------
# 2. Triangle breakout (ascending / descending / symmetrical)
# ---------------------------------------------------------------------------

def detect_triangle_breakout(
    df: pd.DataFrame,
    lookback: int = 40,
    swing_order: int = 3,
    flat_slope_pct: float = 0.0006,
    confirm_pct: float = 0.0008,
) -> list[Signal]:
    """Fits trendlines through recent swing highs and swing lows; if they
    are converging (or one is flat), checks whether the latest close breaks
    the projected upper or lower line."""
    out: list[Signal] = []
    n = len(df)
    if n < lookback + swing_order + 1:
        return out

    for i in range(lookback, n):
        window = df.iloc[i - lookback : i]
        highs = find_swing_highs(window, order=swing_order)
        lows = find_swing_lows(window, order=swing_order)
        if len(highs) < 2 or len(lows) < 2:
            continue

        avg_price = float(window["Close"].mean())
        if avg_price <= 0:
            continue

        slope_hi, intercept_hi = fit_line(highs[-3:] if len(highs) >= 3 else highs)
        slope_lo, intercept_lo = fit_line(lows[-3:] if len(lows) >= 3 else lows)

        norm_slope_hi = slope_hi / avg_price
        norm_slope_lo = slope_lo / avg_price

        hi_flat = abs(norm_slope_hi) <= flat_slope_pct
        lo_flat = abs(norm_slope_lo) <= flat_slope_pct
        hi_falling = norm_slope_hi < -flat_slope_pct
        lo_rising = norm_slope_lo > flat_slope_pct

        if hi_flat and lo_rising:
            shape = "Ascending triangle"
        elif lo_flat and hi_falling:
            shape = "Descending triangle"
        elif hi_falling and lo_rising:
            shape = "Symmetrical triangle"
        else:
            continue  # lines aren't converging in a recognizable way

        # project each line to the current bar's position within `window`
        cur_pos = lookback - 1
        proj_hi = slope_hi * cur_pos + intercept_hi
        proj_lo = slope_lo * cur_pos + intercept_lo
        if proj_hi <= proj_lo:
            continue  # lines have already crossed, no triangle left

        close = float(df["Close"].iloc[i])
        if close > proj_hi * (1 + confirm_pct):
            out.append(
                Signal(
                    pattern=shape,
                    direction="bullish",
                    timestamp=df.index[i],
                    breakout_price=close,
                    level=float(proj_hi),
                    confidence=0.6,
                    note=f"closed above upper trendline at {proj_hi:.2f}",
                )
            )
        elif close < proj_lo * (1 - confirm_pct):
            out.append(
                Signal(
                    pattern=shape,
                    direction="bearish",
                    timestamp=df.index[i],
                    breakout_price=close,
                    level=float(proj_lo),
                    confidence=0.6,
                    note=f"closed below lower trendline at {proj_lo:.2f}",
                )
            )
    return out


# ---------------------------------------------------------------------------
# 3. Double top / double bottom
# ---------------------------------------------------------------------------

def detect_double_top_bottom(
    df: pd.DataFrame,
    lookback: int = 60,
    swing_order: int = 3,
    similarity_pct: float = 0.006,
    confirm_pct: float = 0.0008,
) -> list[Signal]:
    out: list[Signal] = []
    n = len(df)
    if n < lookback + swing_order + 1:
        return out

    for i in range(lookback, n):
        window = df.iloc[i - lookback : i]
        base_pos = i - lookback
        close = float(df["Close"].iloc[i])
        avg_price = float(window["Close"].mean())
        if avg_price <= 0:
            continue

        highs = find_swing_highs(window, order=swing_order)
        if len(highs) >= 2:
            h1, h2 = highs[-2], highs[-1]
            if abs(h1.price - h2.price) / avg_price <= similarity_pct:
                trough_slice = window.iloc[h1.pos : h2.pos + 1]
                if len(trough_slice) >= 3:
                    neckline = float(trough_slice["Low"].min())
                    if close < neckline * (1 - confirm_pct):
                        out.append(
                            Signal(
                                pattern="Double top",
                                direction="bearish",
                                timestamp=df.index[i],
                                breakout_price=close,
                                level=neckline,
                                confidence=0.65,
                                note=(
                                    f"two peaks near {h1.price:.2f}/{h2.price:.2f}, "
                                    f"broke neckline {neckline:.2f}"
                                ),
                            )
                        )

        lows = find_swing_lows(window, order=swing_order)
        if len(lows) >= 2:
            l1, l2 = lows[-2], lows[-1]
            if abs(l1.price - l2.price) / avg_price <= similarity_pct:
                peak_slice = window.iloc[l1.pos : l2.pos + 1]
                if len(peak_slice) >= 3:
                    neckline = float(peak_slice["High"].max())
                    if close > neckline * (1 + confirm_pct):
                        out.append(
                            Signal(
                                pattern="Double bottom",
                                direction="bullish",
                                timestamp=df.index[i],
                                breakout_price=close,
                                level=neckline,
                                confidence=0.65,
                                note=(
                                    f"two troughs near {l1.price:.2f}/{l2.price:.2f}, "
                                    f"broke neckline {neckline:.2f}"
                                ),
                            )
                        )
        del base_pos
    return out


# ---------------------------------------------------------------------------
# 4. Head and shoulders / inverse head and shoulders
# ---------------------------------------------------------------------------

def detect_head_and_shoulders(
    df: pd.DataFrame,
    lookback: int = 80,
    swing_order: int = 3,
    shoulder_similarity_pct: float = 0.012,
    confirm_pct: float = 0.0008,
) -> list[Signal]:
    out: list[Signal] = []
    n = len(df)
    if n < lookback + swing_order + 1:
        return out

    for i in range(lookback, n):
        window = df.iloc[i - lookback : i]
        close = float(df["Close"].iloc[i])
        avg_price = float(window["Close"].mean())
        if avg_price <= 0:
            continue

        highs = find_swing_highs(window, order=swing_order)
        lows = find_swing_lows(window, order=swing_order)

        # regular head & shoulders: three swing highs, middle one tallest
        if len(highs) >= 3:
            left, head, right = highs[-3], highs[-2], highs[-1]
            shoulders_similar = abs(left.price - right.price) / avg_price <= shoulder_similarity_pct
            head_is_higher = head.price > left.price and head.price > right.price
            if shoulders_similar and head_is_higher:
                troughs = [lo for lo in lows if left.pos < lo.pos < right.pos]
                if len(troughs) >= 2:
                    neckline = (troughs[0].price + troughs[-1].price) / 2
                    if close < neckline * (1 - confirm_pct):
                        out.append(
                            Signal(
                                pattern="Head and shoulders",
                                direction="bearish",
                                timestamp=df.index[i],
                                breakout_price=close,
                                level=float(neckline),
                                confidence=0.7,
                                note=f"head {head.price:.2f}, broke neckline {neckline:.2f}",
                            )
                        )

        # inverse head & shoulders: three swing lows, middle one deepest
        if len(lows) >= 3:
            left, head, right = lows[-3], lows[-2], lows[-1]
            shoulders_similar = abs(left.price - right.price) / avg_price <= shoulder_similarity_pct
            head_is_lower = head.price < left.price and head.price < right.price
            if shoulders_similar and head_is_lower:
                peaks = [hi for hi in highs if left.pos < hi.pos < right.pos]
                if len(peaks) >= 2:
                    neckline = (peaks[0].price + peaks[-1].price) / 2
                    if close > neckline * (1 + confirm_pct):
                        out.append(
                            Signal(
                                pattern="Inverse head and shoulders",
                                direction="bullish",
                                timestamp=df.index[i],
                                breakout_price=close,
                                level=float(neckline),
                                confidence=0.7,
                                note=f"head {head.price:.2f}, broke neckline {neckline:.2f}",
                            )
                        )
    return out


# ---------------------------------------------------------------------------
# 5. Opening range breakout (intraday, index-favourite)
# ---------------------------------------------------------------------------

def detect_opening_range_breakout(
    df: pd.DataFrame,
    orb_minutes: int = 15,
    confirm_pct: float = 0.0005,
) -> list[Signal]:
    """Classic intraday index play: mark the high/low of the first
    `orb_minutes` after the 9:15 open, then flag the first close afterwards
    that breaks above/below it. Needs intraday bars (interval <= orb_minutes
    ideally 5m); daily bars will simply produce no signals.
    """
    out: list[Signal] = []
    if df.empty:
        return out

    df = df.copy()
    df["date"] = df.index.date

    for _, day_df in df.groupby("date"):
        if day_df.empty:
            continue
        day_start = day_df.index[0]
        or_cutoff = day_start + pd.Timedelta(minutes=orb_minutes)
        or_window = day_df[day_df.index < or_cutoff]
        rest = day_df[day_df.index >= or_cutoff]
        if or_window.empty or rest.empty:
            continue

        or_high = float(or_window["High"].max())
        or_low = float(or_window["Low"].min())
        triggered = False

        for ts, row in rest.iterrows():
            if triggered:
                break
            close = float(row["Close"])
            if close > or_high * (1 + confirm_pct):
                out.append(
                    Signal(
                        pattern="Opening range breakout",
                        direction="bullish",
                        timestamp=ts,
                        breakout_price=close,
                        level=or_high,
                        confidence=0.55,
                        note=f"broke above first {orb_minutes}-min high {or_high:.2f}",
                    )
                )
                triggered = True
            elif close < or_low * (1 - confirm_pct):
                out.append(
                    Signal(
                        pattern="Opening range breakdown",
                        direction="bearish",
                        timestamp=ts,
                        breakout_price=close,
                        level=or_low,
                        confidence=0.55,
                        note=f"broke below first {orb_minutes}-min low {or_low:.2f}",
                    )
                )
                triggered = True
    return out


DETECTORS = {
    "range": detect_range_breakout,
    "triangle": detect_triangle_breakout,
    "double": detect_double_top_bottom,
    "head_shoulders": detect_head_and_shoulders,
    "orb": detect_opening_range_breakout,
}


def detect_all(
    df: pd.DataFrame,
    index_key: str,
    interval: str,
    enabled: list[str] | None = None,
    params: dict[str, dict] | None = None,
) -> list[Signal]:
    """Run the requested detectors (default: all) over `df` and stamp each
    resulting Signal with the index key and interval it came from."""
    enabled = enabled or list(DETECTORS.keys())
    params = params or {}
    signals: list[Signal] = []
    for name in enabled:
        fn = DETECTORS[name]
        kwargs = params.get(name, {})
        for sig in fn(df, **kwargs):
            sig.index_key = index_key
            sig.interval = interval
            signals.append(sig)
    signals.sort(key=lambda s: s.timestamp)
    return signals
