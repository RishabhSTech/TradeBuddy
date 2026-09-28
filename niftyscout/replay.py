"""
Replay a detector against historical bars and see, in hindsight, how its
signals would have played out. This is NOT a proper backtest (no slippage,
no costs, one fixed exit rule) — it's a sanity check so you can eyeball
whether a pattern is worth watching for before you start acting on live
alerts.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .patterns import Signal, detect_all


@dataclass
class ReplayResult:
    signal: Signal
    forward_return_pct: float
    hit: bool  # did price move in the signalled direction by the horizon?


def replay(
    df: pd.DataFrame,
    index_key: str,
    interval: str,
    horizon_bars: int = 10,
    enabled: list[str] | None = None,
    params: dict[str, dict] | None = None,
) -> list[ReplayResult]:
    signals = detect_all(df, index_key, interval, enabled=enabled, params=params)
    results = []
    closes = df["Close"]
    idx = df.index

    for sig in signals:
        if sig.timestamp not in idx:
            continue
        pos = idx.get_loc(sig.timestamp)
        target_pos = pos + horizon_bars
        if target_pos >= len(df):
            continue  # not enough future data yet
        entry = closes.iloc[pos]
        exit_ = closes.iloc[target_pos]
        move_pct = (exit_ - entry) / entry * 100
        hit = move_pct > 0 if sig.direction == "bullish" else move_pct < 0
        results.append(ReplayResult(sig, round(float(move_pct), 3), hit))
    return results


def summarize(results: list[ReplayResult]) -> dict:
    if not results:
        return {"count": 0}
    by_pattern: dict[str, list[ReplayResult]] = {}
    for r in results:
        by_pattern.setdefault(r.signal.pattern, []).append(r)

    summary = {"count": len(results), "patterns": {}}
    for pattern, rs in by_pattern.items():
        hits = sum(1 for r in rs if r.hit)
        avg_move = sum(r.forward_return_pct for r in rs) / len(rs)
        summary["patterns"][pattern] = {
            "signals": len(rs),
            "hit_rate_pct": round(100 * hits / len(rs), 1),
            "avg_forward_return_pct": round(avg_move, 3),
        }
    return summary
