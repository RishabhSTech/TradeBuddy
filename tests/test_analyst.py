from types import SimpleNamespace

from niftyscout.analyst import DEFAULT_DISCLAIMER, build_analyst_note


def _signal(direction="bullish", pattern="Range breakout"):
    return SimpleNamespace(
        index_key="NIFTY",
        interval="15m",
        direction=direction,
        pattern=pattern,
        breakout_price=24850.0,
    )


def _indicators(rel_volume=1.8, trend_direction="up", rsi14=61.0):
    return SimpleNamespace(rel_volume=rel_volume, trend_direction=trend_direction, rsi14=rsi14)


def _plan(target2=None, r2=None):
    return SimpleNamespace(stop=24790.0, target1=24980.0, r_multiple_1=1.9, target2=target2, r_multiple_2=r2)


def test_note_always_ends_with_the_disclaimer():
    note = build_analyst_note(_signal(), _indicators(), _plan())
    assert note.endswith(DEFAULT_DISCLAIMER)


def test_note_mentions_index_and_price():
    note = build_analyst_note(_signal(), _indicators(), _plan())
    assert "NIFTY" in note
    assert "24850.00" in note


def test_note_flags_low_volume():
    note = build_analyst_note(_signal(), _indicators(rel_volume=0.5), _plan())
    assert "light volume" in note


def test_note_flags_trend_alignment():
    note = build_analyst_note(_signal(direction="bullish"), _indicators(trend_direction="up"), _plan())
    assert "aligned with an uptrend" in note


def test_note_flags_counter_trend():
    note = build_analyst_note(_signal(direction="bullish"), _indicators(trend_direction="down"), _plan())
    assert "against a downtrend" in note


def test_note_includes_stop_and_target_when_plan_present():
    note = build_analyst_note(_signal(), _indicators(), _plan())
    assert "Stop 24790.00" in note
    assert "1.9R" in note


def test_note_omits_trade_structure_when_plan_is_none():
    note = build_analyst_note(_signal(), _indicators(), None)
    assert "Stop" not in note


def test_note_includes_stretch_target_when_target2_present():
    note = build_analyst_note(_signal(), _indicators(), _plan(target2=25100.0, r2=3.2))
    assert "stretch target 25100.00" in note


def test_note_handles_missing_indicators_gracefully():
    note = build_analyst_note(_signal(), None, None)
    assert note.startswith("NIFTY 15m bullish range breakout")
    assert note.endswith(DEFAULT_DISCLAIMER)
