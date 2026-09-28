import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from niftyscout.patterns import (
    detect_range_breakout,
    detect_triangle_breakout,
    detect_double_top_bottom,
    detect_head_and_shoulders,
    detect_opening_range_breakout,
)
from tests import synth


def test_range_breakout_detected():
    df = synth.make_range_then_breakout()
    signals = detect_range_breakout(df, lookback=20, max_range_pct=0.02, confirm_pct=0.0005)
    assert signals, "expected at least one range breakout signal"
    last = signals[-1]
    assert last.direction == "bullish"
    assert last.timestamp == df.index[-1]


def test_range_no_signal_when_flat():
    idx = synth._to_df.__wrapped__ if False else None  # noop, keep flake quiet
    import numpy as np

    flat = synth._to_df(np.full(40, 100.0), wobble=0.05)
    signals = detect_range_breakout(flat, lookback=20, max_range_pct=0.02, confirm_pct=0.0005)
    assert signals == []


def test_ascending_triangle_detected():
    df = synth.make_ascending_triangle()
    lookback = len(df) - 3
    signals = detect_triangle_breakout(
        df, lookback=lookback, swing_order=2, flat_slope_pct=0.001, confirm_pct=0.0005
    )
    assert any(s.direction == "bullish" for s in signals), signals
    assert any("Ascending" in s.pattern or "Symmetrical" in s.pattern for s in signals)


def test_double_top_detected():
    df = synth.make_double_top()
    lookback = len(df) - 3
    signals = detect_double_top_bottom(df, lookback=lookback, swing_order=2, similarity_pct=0.02)
    assert any(s.pattern == "Double top" and s.direction == "bearish" for s in signals), signals


def test_double_bottom_detected():
    df = synth.make_double_bottom()
    lookback = len(df) - 3
    signals = detect_double_top_bottom(df, lookback=lookback, swing_order=2, similarity_pct=0.02)
    assert any(s.pattern == "Double bottom" and s.direction == "bullish" for s in signals), signals


def test_head_and_shoulders_detected():
    df = synth.make_head_and_shoulders()
    lookback = len(df) - 3
    signals = detect_head_and_shoulders(
        df, lookback=lookback, swing_order=2, shoulder_similarity_pct=0.03
    )
    assert any(s.pattern == "Head and shoulders" for s in signals), signals


def test_opening_range_breakout_detected():
    df = synth.make_opening_range_breakout()
    signals = detect_opening_range_breakout(df, orb_minutes=15, confirm_pct=0.001)
    assert signals, "expected an ORB signal"
    assert signals[0].direction == "bullish"


def test_signal_headline_readable():
    df = synth.make_range_then_breakout()
    signals = detect_range_breakout(df, lookback=20, max_range_pct=0.02, confirm_pct=0.0005)
    signals[-1].index_key = "NIFTY"
    signals[-1].interval = "15m"
    text = signals[-1].headline()
    assert "NIFTY" in text and "breakout" in text.lower()
