"""
Volume profile: where volume actually traded across the price range of a
lookback window, not just where price closed. Gives two things the swing-
point geometry in `swings.py` can't: a Point of Control (POC, the
highest-volume price) and a Value Area (VAH/VAL, the band holding most of
the volume) -- useful as extra support/resistance for `levels.py`'s target
selection.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class VolumeProfileLevel:
    price_low: float
    price_high: float
    volume: float


@dataclass
class VolumeProfile:
    poc: float           # price of the highest-volume bin
    vah: float           # value-area high
    val: float           # value-area low
    total_volume: float
    bins: list[VolumeProfileLevel]


def compute_volume_profile(
    df: pd.DataFrame, bins: int = 24, value_area_pct: float = 0.70
) -> VolumeProfile:
    """Histograms typical price `(H+L+C)/3`, weighted by volume, into `bins`
    buckets spanning the window's full High/Low range. POC is the bucket
    with the most volume; VAH/VAL expand outward from POC, bucket by
    bucket (always taking whichever side has more volume next), until
    `value_area_pct` of the window's total volume is enclosed.
    """
    price_low = float(df["Low"].min())
    price_high = float(df["High"].max())
    if not np.isfinite(price_low) or not np.isfinite(price_high):
        raise ValueError("compute_volume_profile: no valid High/Low data in window")
    if price_high <= price_low:
        price_high = price_low + max(abs(price_low) * 1e-6, 1e-6)

    edges = np.linspace(price_low, price_high, bins + 1)
    typical = ((df["High"] + df["Low"] + df["Close"]) / 3.0).to_numpy()
    volume = df["Volume"].to_numpy(dtype=float)

    bin_idx = np.clip(np.digitize(typical, edges) - 1, 0, bins - 1)
    vol_per_bin = np.zeros(bins)
    np.add.at(vol_per_bin, bin_idx, volume)

    total = float(vol_per_bin.sum())
    poc_idx = int(np.argmax(vol_per_bin))

    included = {poc_idx}
    covered = vol_per_bin[poc_idx]
    left, right = poc_idx - 1, poc_idx + 1
    target = value_area_pct * total if total > 0 else 0.0
    while covered < target and (left >= 0 or right < bins):
        left_vol = vol_per_bin[left] if left >= 0 else -1.0
        right_vol = vol_per_bin[right] if right < bins else -1.0
        if right_vol >= left_vol and right < bins:
            included.add(right)
            covered += vol_per_bin[right]
            right += 1
        elif left >= 0:
            included.add(left)
            covered += vol_per_bin[left]
            left -= 1
        else:
            break

    val_idx, vah_idx = min(included), max(included)
    bin_levels = [
        VolumeProfileLevel(price_low=float(edges[i]), price_high=float(edges[i + 1]), volume=float(vol_per_bin[i]))
        for i in range(bins)
    ]

    return VolumeProfile(
        poc=float((edges[poc_idx] + edges[poc_idx + 1]) / 2),
        vah=float(edges[vah_idx + 1]),
        val=float(edges[val_idx]),
        total_volume=total,
        bins=bin_levels,
    )


def nearest_level(profile: VolumeProfile, price: float, direction: str) -> float | None:
    """Nearest of {POC, VAH, VAL} strictly beyond `price` in the breakout
    direction ("bullish" looks above, "bearish" looks below); `None` if none
    qualify."""
    candidates = [profile.poc, profile.vah, profile.val]
    if direction == "bullish":
        beyond = [c for c in candidates if c > price]
        return min(beyond) if beyond else None
    beyond = [c for c in candidates if c < price]
    return max(beyond) if beyond else None
