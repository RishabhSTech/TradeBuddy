import numpy as np
import pandas as pd

from niftyscout.volume_profile import compute_volume_profile, nearest_level


def _df(prices, volumes):
    n = len(prices)
    idx = pd.date_range("2026-01-01 09:15", periods=n, freq="15min", tz="Asia/Kolkata")
    prices = np.asarray(prices, dtype=float)
    return pd.DataFrame(
        {
            "Open": prices,
            "High": prices + 0.25,
            "Low": prices - 0.25,
            "Close": prices,
            "Volume": np.asarray(volumes, dtype=float),
        },
        index=idx,
    )


def test_poc_lands_where_volume_is_concentrated():
    # most bars trade near 100, a few stray bars trade far away with tiny volume
    prices = [100.0] * 15 + [80.0, 120.0, 85.0, 115.0]
    volumes = [10_000.0] * 15 + [100.0, 100.0, 100.0, 100.0]
    df = _df(prices, volumes)

    profile = compute_volume_profile(df, bins=20, value_area_pct=0.70)

    assert 95.0 <= profile.poc <= 105.0
    assert profile.val <= profile.poc <= profile.vah


def test_value_area_encloses_at_least_the_requested_share_of_volume():
    prices = list(np.linspace(90, 110, 40))
    volumes = [100.0] * 40
    df = _df(prices, volumes)

    profile = compute_volume_profile(df, bins=20, value_area_pct=0.70)

    enclosed = sum(b.volume for b in profile.bins if profile.val <= (b.price_low + b.price_high) / 2 <= profile.vah)
    assert enclosed / profile.total_volume >= 0.70 - 1e-9


def test_degenerate_flat_price_does_not_crash():
    df = _df([100.0] * 10, [500.0] * 10)
    profile = compute_volume_profile(df, bins=10)
    assert profile.total_volume == 5000.0
    assert profile.val <= profile.poc <= profile.vah


def test_nearest_level_bullish_looks_above_price():
    prices = [100.0] * 15 + [80.0, 120.0]
    volumes = [10_000.0] * 15 + [100.0, 100.0]
    profile = compute_volume_profile(_df(prices, volumes), bins=20)

    level = nearest_level(profile, price=95.0, direction="bullish")
    assert level is not None and level > 95.0


def test_nearest_level_bearish_looks_below_price():
    prices = [100.0] * 15 + [80.0, 120.0]
    volumes = [10_000.0] * 15 + [100.0, 100.0]
    profile = compute_volume_profile(_df(prices, volumes), bins=20)

    level = nearest_level(profile, price=105.0, direction="bearish")
    assert level is not None and level < 105.0


def test_nearest_level_returns_none_when_nothing_qualifies():
    prices = [100.0] * 15
    volumes = [1000.0] * 15
    profile = compute_volume_profile(_df(prices, volumes), bins=10)

    assert nearest_level(profile, price=10_000.0, direction="bullish") is None
