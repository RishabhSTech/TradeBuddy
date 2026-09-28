"""
Technical indicators computed once per scan and shared across all detectors:
momentum (RSI, MACD), trend (EMA stack), volatility (ATR), and volume
(relative volume, OBV, session VWAP).

Everything here is pure math over the OHLCV DataFrame the rest of the app
already has -- no external calls, no chart-image analysis. `compute_indicators`
is the one entry point detectors/chart rendering should call; the individual
functions (`rsi`, `ema`, ...) are exposed separately mainly for testing.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window, min_periods=1).mean()


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI. Flat stretches (no gains AND no losses) read as neutral
    (50) rather than NaN/inf; stretches with gains but zero losses read as
    100 (maxed out) rather than a division-by-zero NaN."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = avg_gain / avg_loss
        out = 100 - (100 / (1 + rs))
    out = out.where(avg_loss != 0, 100.0)
    out = out.where(~((avg_gain == 0) & (avg_loss == 0)), 50.0)
    return out


def macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.DataFrame:
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = ema(macd_line, signal)
    return pd.DataFrame(
        {"macd": macd_line, "signal": signal_line, "hist": macd_line - signal_line}
    )


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder-smoothed Average True Range -- the volatility unit `levels.py`
    sizes stops off of."""
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def vwap(df: pd.DataFrame, session_reset: bool = True) -> pd.Series:
    """Volume-weighted average price. `session_reset=True` restarts the
    cumulative sums at each calendar-day boundary, which is what "VWAP" means
    for intraday bars; only meaningful when there are multiple bars per
    session (see `compute_indicators`, which skips this for daily bars)."""
    typical = (df["High"] + df["Low"] + df["Close"]) / 3.0
    price_volume = typical * df["Volume"]
    if session_reset:
        session = pd.Series(df.index.date, index=df.index)
        cum_pv = price_volume.groupby(session).cumsum()
        cum_vol = df["Volume"].groupby(session).cumsum()
    else:
        cum_pv = price_volume.cumsum()
        cum_vol = df["Volume"].cumsum()
    with np.errstate(divide="ignore", invalid="ignore"):
        return cum_pv / cum_vol


def obv(df: pd.DataFrame) -> pd.Series:
    """On-Balance Volume: running total of volume signed by the day's close
    direction. Used for its slope/trend, not its absolute level."""
    direction = np.sign(df["Close"].diff().fillna(0))
    return (direction * df["Volume"]).cumsum()


def relative_volume(volume: pd.Series, window: int = 20) -> pd.Series:
    """Current bar's volume as a multiple of its own rolling average. Index
    volume is a proxy figure, not a traded contract's volume, so every
    volume check in this codebase uses this relative measure -- never a
    fixed absolute threshold."""
    avg = volume.rolling(window, min_periods=1).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        return volume / avg


def trend_context(
    close: pd.Series, ema_fast: pd.Series, ema_slow: pd.Series, ema_trend: pd.Series
) -> tuple[pd.Series, pd.Series]:
    """Classifies the EMA stack into a trend direction + a 0-1 strength score.

    "up": fast > slow > trend (bullish EMA stack). "down": fast < slow < trend.
    Anything else (stack not fully aligned) is "flat" -- a range/transition.
    Strength is the fast-vs-trend spread normalized by price so it's
    comparable across NIFTY/BANKNIFTY/SENSEX regardless of index level.
    """
    aligned_up = (ema_fast > ema_slow) & (ema_slow > ema_trend)
    aligned_down = (ema_fast < ema_slow) & (ema_slow < ema_trend)
    direction = pd.Series(
        np.select([aligned_up, aligned_down], ["up", "down"], default="flat"),
        index=close.index,
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        spread_pct = ((ema_fast - ema_trend) / close).abs()
    strength = (spread_pct * 20).clip(0, 1).fillna(0.0)  # ~5% spread maxes out strength
    return direction, strength


# Daily+ bars are one bar per session, so a "session VWAP" would just equal
# that bar's own typical price -- not meaningful. Only compute it intraday.
_INTRADAY_INTERVALS_EXCLUDE = {"1d", "5d", "1wk", "1mo", "3mo"}


def compute_indicators(
    df: pd.DataFrame,
    interval: str = "15m",
    rsi_period: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    ema_fast: int = 20,
    ema_slow: int = 50,
    ema_trend: int = 200,
    atr_period: int = 14,
    rel_volume_window: int = 20,
) -> pd.DataFrame:
    """One indicator frame aligned to `df.index`, computed once per scan
    pass and shared by every detector (see `patterns.detect_all`) instead of
    each detector recomputing it inside its own O(n * lookback) loop."""
    close = df["Close"]
    out = pd.DataFrame(index=df.index)

    out["rsi14"] = rsi(close, rsi_period)

    macd_df = macd(close, macd_fast, macd_slow, macd_signal)
    out["macd"] = macd_df["macd"]
    out["macd_signal"] = macd_df["signal"]
    out["macd_hist"] = macd_df["hist"]

    out["ema_fast"] = ema(close, ema_fast)
    out["ema_slow"] = ema(close, ema_slow)
    out["ema_trend"] = ema(close, ema_trend)

    out["atr14"] = atr(df, atr_period)
    out["rel_volume"] = relative_volume(df["Volume"], rel_volume_window)
    out["obv"] = obv(df)

    out["vwap"] = (
        vwap(df, session_reset=True) if interval not in _INTRADAY_INTERVALS_EXCLUDE else np.nan
    )

    direction, strength = trend_context(close, out["ema_fast"], out["ema_slow"], out["ema_trend"])
    out["trend_direction"] = direction
    out["trend_strength"] = strength

    return out


@dataclass
class IndicatorSnapshot:
    rsi14: float | None
    macd: float | None
    macd_signal: float | None
    macd_hist: float | None
    ema_fast: float | None
    ema_slow: float | None
    ema_trend: float | None
    atr14: float | None
    vwap: float | None
    rel_volume: float | None
    obv: float | None
    trend_direction: str
    trend_strength: float


def _clean_float(value) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if np.isnan(f) else f


def snapshot_at(ind: pd.DataFrame, pos: int) -> IndicatorSnapshot:
    """Pulls a single bar's worth of `compute_indicators` output into a
    plain dataclass -- what gets attached to an individual Signal."""
    row = ind.iloc[pos]
    return IndicatorSnapshot(
        rsi14=_clean_float(row.get("rsi14")),
        macd=_clean_float(row.get("macd")),
        macd_signal=_clean_float(row.get("macd_signal")),
        macd_hist=_clean_float(row.get("macd_hist")),
        ema_fast=_clean_float(row.get("ema_fast")),
        ema_slow=_clean_float(row.get("ema_slow")),
        ema_trend=_clean_float(row.get("ema_trend")),
        atr14=_clean_float(row.get("atr14")),
        vwap=_clean_float(row.get("vwap")),
        rel_volume=_clean_float(row.get("rel_volume")),
        obv=_clean_float(row.get("obv")),
        trend_direction=str(row.get("trend_direction", "flat")),
        trend_strength=float(row.get("trend_strength", 0.0) or 0.0),
    )
