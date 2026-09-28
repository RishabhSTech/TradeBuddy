from types import SimpleNamespace

import numpy as np
import pandas as pd

from niftyscout.levels import build_trade_plan
from niftyscout.volume_profile import compute_volume_profile


def _signal(direction, breakout_price, level, pattern_height=None):
    return SimpleNamespace(
        direction=direction,
        breakout_price=breakout_price,
        level=level,
        pattern_height=pattern_height,
    )


def _ind(atr14):
    return SimpleNamespace(atr14=atr14)


def _flat_df(n=60, price=100.0):
    idx = pd.date_range("2026-01-01 09:15", periods=n, freq="15min", tz="Asia/Kolkata")
    return pd.DataFrame(
        {
            "Open": [price] * n,
            "High": [price + 0.5] * n,
            "Low": [price - 0.5] * n,
            "Close": [price] * n,
            "Volume": [1000.0] * n,
        },
        index=idx,
    )


def test_atr_stop_placed_beyond_broken_level_bullish():
    sig = _signal("bullish", breakout_price=103.0, level=100.0, pattern_height=5.0)
    plan = build_trade_plan(sig, _flat_df(), _ind(atr14=2.0), atr_stop_mult=0.5, tick_size=0.01)
    assert plan is not None
    assert plan.stop == 99.0  # 100 - 0.5*2.0
    assert plan.method.startswith("atr_stop")


def test_atr_stop_placed_beyond_broken_level_bearish():
    sig = _signal("bearish", breakout_price=97.0, level=100.0, pattern_height=5.0)
    plan = build_trade_plan(sig, _flat_df(), _ind(atr14=2.0), atr_stop_mult=0.5, tick_size=0.01)
    assert plan is not None
    assert plan.stop == 101.0  # 100 + 0.5*2.0


def test_target1_is_measured_move_from_pattern_height():
    sig = _signal("bullish", breakout_price=103.0, level=100.0, pattern_height=5.0)
    plan = build_trade_plan(sig, _flat_df(), _ind(atr14=2.0), measured_move_mult=1.0, tick_size=0.01)
    assert plan is not None
    assert abs(plan.target1 - 108.0) < 1e-6  # 103 + 5.0


def test_bearish_target1_projects_downward():
    sig = _signal("bearish", breakout_price=97.0, level=100.0, pattern_height=5.0)
    plan = build_trade_plan(sig, _flat_df(), _ind(atr14=2.0), measured_move_mult=1.0, tick_size=0.01)
    assert plan is not None
    assert abs(plan.target1 - 92.0) < 1e-6  # 97 - 5.0


def test_risk_reward_arithmetic():
    sig = _signal("bullish", breakout_price=103.0, level=100.0, pattern_height=5.0)
    plan = build_trade_plan(sig, _flat_df(), _ind(atr14=2.0), atr_stop_mult=0.5, tick_size=0.01)
    assert plan is not None
    assert abs(plan.risk_per_unit - (103.0 - 99.0)) < 1e-6
    assert abs(plan.reward_to_target1 - (108.0 - 103.0)) < 1e-6
    assert abs(plan.r_multiple_1 - (plan.reward_to_target1 / plan.risk_per_unit)) < 1e-6


def test_falls_back_to_swing_stop_when_atr_unavailable():
    n = 60
    idx = pd.date_range("2026-01-01 09:15", periods=n, freq="15min", tz="Asia/Kolkata")
    closes = np.array([100.0] * n)
    # carve a clean swing low at 95 a few bars before "now"
    closes[40] = 95.0
    highs = closes + 0.5
    lows = closes - 0.5
    lows[40] = 94.5
    df = pd.DataFrame(
        {"Open": closes, "High": highs, "Low": lows, "Close": closes, "Volume": [1000.0] * n},
        index=idx,
    )
    sig = _signal("bullish", breakout_price=103.0, level=100.0, pattern_height=5.0)
    plan = build_trade_plan(sig, df, _ind(atr14=None), tick_size=0.01)
    assert plan is not None
    assert plan.stop < 100.0
    assert plan.method.startswith("swing_stop")


def test_returns_none_when_no_stop_can_be_placed():
    sig = _signal("bullish", breakout_price=103.0, level=100.0, pattern_height=5.0)
    plan = build_trade_plan(sig, _flat_df(), _ind(atr14=None), tick_size=0.01)
    assert plan is None


def test_target2_uses_nearest_volume_profile_level_beyond_target1():
    n = 60
    idx = pd.date_range("2026-01-01 09:15", periods=n, freq="15min", tz="Asia/Kolkata")
    prices = np.full(n, 100.0)
    volumes = np.full(n, 1000.0)
    # a high-volume node clearly beyond target1 (103+5=108)
    prices[10] = 115.0
    volumes[10] = 50_000.0
    df = pd.DataFrame(
        {
            "Open": prices,
            "High": prices + 0.5,
            "Low": prices - 0.5,
            "Close": prices,
            "Volume": volumes,
        },
        index=idx,
    )
    vp = compute_volume_profile(df, bins=30)
    sig = _signal("bullish", breakout_price=103.0, level=100.0, pattern_height=5.0)
    plan = build_trade_plan(sig, df, _ind(atr14=2.0), volume_profile=vp, tick_size=0.01)
    assert plan is not None
    assert plan.target2 is not None
    assert plan.target2 > plan.target1
