"""
Turns a Signal + its IndicatorSnapshot + TradePlan into one plain-English
paragraph -- the "pro analyst" narration. This is pure string formatting
over already-computed numbers: no model call, fully deterministic, and the
same inputs always produce the same sentence.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .indicators import IndicatorSnapshot
    from .levels import TradePlan
    from .patterns import Signal

DEFAULT_DISCLAIMER = (
    "Structure-derived levels from the pattern's own geometry and volatility "
    "-- not investment advice."
)


def _volume_phrase(rel_volume: float | None) -> str | None:
    if rel_volume is None:
        return None
    if rel_volume >= 1.5:
        return f"confirmed by {rel_volume:.1f}x average volume"
    if rel_volume <= 0.7:
        return f"on light volume ({rel_volume:.1f}x average, worth watching for a false break)"
    return f"on roughly average volume ({rel_volume:.1f}x)"


def _trend_phrase(direction: str | None, signal_direction: str) -> str | None:
    if not direction or direction == "flat":
        return None
    aligned = (direction == "up" and signal_direction == "bullish") or (
        direction == "down" and signal_direction == "bearish"
    )
    label = "an uptrend" if direction == "up" else "a downtrend"
    return f"aligned with {label} on the higher EMA stack" if aligned else f"against {label} on the higher EMA stack"


def _rsi_phrase(rsi14: float | None) -> str | None:
    if rsi14 is None:
        return None
    if rsi14 >= 70:
        return f"RSI(14) at {rsi14:.0f} (overbought territory)"
    if rsi14 <= 30:
        return f"RSI(14) at {rsi14:.0f} (oversold territory)"
    return f"RSI(14) at {rsi14:.0f}"


def build_analyst_note(
    signal: "Signal",
    indicators: "IndicatorSnapshot | None",
    plan: "TradePlan | None",
    disclaimer: str = DEFAULT_DISCLAIMER,
) -> str:
    parts: list[str] = []

    lead = f"{signal.index_key} {signal.interval} {signal.direction} {signal.pattern.lower()} at {signal.breakout_price:.2f}"
    clauses = []
    if indicators is not None:
        vol = _volume_phrase(indicators.rel_volume)
        if vol:
            clauses.append(vol)
        trend = _trend_phrase(indicators.trend_direction, signal.direction)
        if trend:
            clauses.append(trend)
        rsi_phrase = _rsi_phrase(indicators.rsi14)
        if rsi_phrase:
            clauses.append(rsi_phrase)
    if clauses:
        lead += ", " + "; ".join(clauses) + "."
    else:
        lead += "."
    parts.append(lead)

    if plan is not None:
        target_bit = f"target {plan.target1:.2f} ({plan.r_multiple_1:.1f}R)"
        if plan.target2 is not None and plan.r_multiple_2 is not None:
            target_bit += f", stretch target {plan.target2:.2f} ({plan.r_multiple_2:.1f}R)"
        parts.append(f"Stop {plan.stop:.2f}, {target_bit}.")

    parts.append(disclaimer)
    return " ".join(parts)
