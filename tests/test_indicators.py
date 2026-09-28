import numpy as np
import pandas as pd

from niftyscout.indicators import (
    atr,
    compute_indicators,
    ema,
    macd,
    obv,
    relative_volume,
    rsi,
    sma,
    trend_context,
    vwap,
)


def _df(closes, highs=None, lows=None, volumes=None, freq="1min", start="2026-01-01 09:15"):
    closes = np.asarray(closes, dtype=float)
    n = len(closes)
    idx = pd.date_range(start=start, periods=n, freq=freq, tz="Asia/Kolkata")
    highs = np.asarray(highs, dtype=float) if highs is not None else closes + 0.1
    lows = np.asarray(lows, dtype=float) if lows is not None else closes - 0.1
    opens = np.roll(closes, 1)
    opens[0] = closes[0]
    volumes = np.asarray(volumes, dtype=float) if volumes is not None else np.full(n, 1000.0)
    return pd.DataFrame(
        {"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volumes}, index=idx
    )


def test_sma_matches_manual_average():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    out = sma(s, window=3)
    assert out.iloc[-1] == (3 + 4 + 5) / 3


def test_ema_reacts_faster_than_sma_to_a_jump():
    s = pd.Series([100.0] * 20 + [110.0] * 5)
    e = ema(s, span=10)
    m = sma(s, window=10)
    assert e.iloc[-1] > m.iloc[-1]


def test_rsi_is_100_on_a_pure_uptrend():
    s = pd.Series([100 + i for i in range(30)], dtype=float)
    out = rsi(s, period=14)
    assert out.iloc[-1] == 100.0


def test_rsi_is_neutral_on_flat_series():
    s = pd.Series([100.0] * 30)
    out = rsi(s, period=14)
    assert out.iloc[-1] == 50.0


def test_rsi_drops_on_a_pure_downtrend():
    s = pd.Series([200 - i for i in range(30)], dtype=float)
    out = rsi(s, period=14)
    assert out.iloc[-1] == 0.0


def test_macd_hist_positive_when_fast_ema_above_slow():
    s = pd.Series([100.0] * 30 + [100 + i for i in range(30)])
    out = macd(s, fast=5, slow=10, signal=3)
    assert out["hist"].iloc[-1] > 0


def test_atr_tracks_a_known_constant_range():
    # High-Low is a constant 2.0 every bar, no gaps vs prior close -> ATR settles at 2.0
    closes = np.full(30, 100.0)
    df = _df(closes, highs=closes + 1.0, lows=closes - 1.0)
    out = atr(df, period=14)
    assert abs(out.iloc[-1] - 2.0) < 1e-6


def test_relative_volume_flags_a_spike():
    volumes = [1000.0] * 20 + [5000.0]
    df = _df(np.full(21, 100.0), volumes=volumes)
    out = relative_volume(df["Volume"], window=20)
    assert out.iloc[-1] > 3.0


def test_obv_rises_on_up_closes():
    closes = [100, 101, 102, 103, 104]
    df = _df(closes)
    out = obv(df)
    assert out.iloc[-1] > out.iloc[0]


def test_vwap_matches_manual_weighted_average_within_one_session():
    highs = [101, 102, 103]
    lows = [99, 100, 101]
    closes = [100, 101, 102]
    volumes = [10, 20, 30]
    df = _df(closes, highs=highs, lows=lows, volumes=volumes, freq="15min")
    out = vwap(df, session_reset=True)

    typical = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
    manual_final = sum(t * v for t, v in zip(typical, volumes)) / sum(volumes)
    assert abs(out.iloc[-1] - manual_final) < 1e-9


def test_vwap_resets_across_a_session_boundary():
    # two 1-bar "sessions" a day apart -> second bar's VWAP is just its own
    # typical price, not blended with the first day's
    df = _df(
        [100.0, 200.0],
        highs=[100.0, 200.0],
        lows=[100.0, 200.0],
        volumes=[10.0, 10.0],
        freq="1D",
    )
    out = vwap(df, session_reset=True)
    assert abs(out.iloc[-1] - 200.0) < 1e-9


def test_trend_context_detects_aligned_uptrend():
    close = pd.Series([100.0])
    ema_fast = pd.Series([110.0])
    ema_slow = pd.Series([105.0])
    ema_trend = pd.Series([100.0])
    direction, strength = trend_context(close, ema_fast, ema_slow, ema_trend)
    assert direction.iloc[0] == "up"
    assert 0.0 < strength.iloc[0] <= 1.0


def test_trend_context_flat_when_stack_not_aligned():
    close = pd.Series([100.0])
    ema_fast = pd.Series([105.0])
    ema_slow = pd.Series([100.0])
    ema_trend = pd.Series([103.0])  # fast > trend > slow -- not a clean stack
    direction, _ = trend_context(close, ema_fast, ema_slow, ema_trend)
    assert direction.iloc[0] == "flat"


def test_compute_indicators_skips_vwap_on_daily_bars():
    df = _df([100.0] * 30, freq="1D")
    out = compute_indicators(df, interval="1d")
    assert out["vwap"].isna().all()


def test_compute_indicators_fills_vwap_on_intraday_bars():
    df = _df([100.0] * 30, freq="15min")
    out = compute_indicators(df, interval="15m")
    assert out["vwap"].notna().any()


def test_compute_indicators_runs_on_short_flat_series_without_crashing():
    # mirrors the existing test_range_no_signal_when_flat fixture shape
    df = _df([100.0] * 40, highs=[100.05] * 40, lows=[99.95] * 40, freq="15min")
    out = compute_indicators(df, interval="15m")
    assert len(out) == 40
    assert not out["rsi14"].isna().all()
