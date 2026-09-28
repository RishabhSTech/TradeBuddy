"""
Renders a chart PNG for a signal: price + volume panes, the broken level,
EMA/VWAP overlays, and -- when the signal was enriched by `detect_all` --
the entry/stop/target lines from `levels.py` and the POC/VAH/VAL lines from
`volume_profile.py`. Sent alongside Telegram alerts and shown in the
dashboard so you can eyeball the whole picture before deciding anything.

Degrades gracefully: a signal with no `plan`/`volume_levels` (old cached
signals, or data too short for indicators to warm up) just renders without
those overlays -- never an error.
"""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .indicators import compute_indicators
from .patterns import Signal


def render_signal_chart(
    df: pd.DataFrame,
    signal: Signal,
    out_dir: str = "charts",
    context_bars: int = 60,
) -> str:
    os.makedirs(out_dir, exist_ok=True)

    if signal.timestamp in df.index:
        end_pos = df.index.get_loc(signal.timestamp)
        if isinstance(end_pos, slice):
            end_pos = end_pos.stop - 1
    else:
        end_pos = len(df) - 1
    start_pos = max(0, end_pos - context_bars)
    window = df.iloc[start_pos : end_pos + 1]

    ind = compute_indicators(window, interval=signal.interval or "15m")

    fig, (ax, vol_ax) = plt.subplots(
        2,
        1,
        figsize=(9, 5.5),
        dpi=130,
        sharex=True,
        gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08},
        constrained_layout=True,
    )

    ax.plot(window.index, window["Close"], color="#2563eb", linewidth=1.4, label="Close", zorder=3)
    if ind["ema_fast"].notna().any():
        ax.plot(window.index, ind["ema_fast"], color="#f59e0b", linewidth=1.0, label="EMA fast", zorder=2)
    if ind["ema_slow"].notna().any():
        ax.plot(window.index, ind["ema_slow"], color="#a855f7", linewidth=1.0, label="EMA slow", zorder=2)
    if ind["vwap"].notna().any():
        ax.plot(window.index, ind["vwap"], color="#0ea5e9", linewidth=1.0, linestyle=":", label="VWAP", zorder=2)

    ax.axhline(signal.level, color="#94a3b8", linestyle="--", linewidth=1, label=f"Level {signal.level:.2f}")

    if signal.volume_levels:
        poc = signal.volume_levels.get("poc")
        vah = signal.volume_levels.get("vah")
        val = signal.volume_levels.get("val")
        if poc is not None:
            ax.axhline(poc, color="#64748b", linestyle="-", linewidth=0.8, alpha=0.6, label=f"POC {poc:.2f}")
        if vah is not None:
            ax.axhline(vah, color="#64748b", linestyle=":", linewidth=0.7, alpha=0.5)
        if val is not None:
            ax.axhline(val, color="#64748b", linestyle=":", linewidth=0.7, alpha=0.5)

    if signal.plan:
        plan = signal.plan
        ax.axhline(plan.stop, color="#dc2626", linestyle="--", linewidth=1, alpha=0.85, label=f"Stop {plan.stop:.2f}")
        ax.axhline(
            plan.target1, color="#16a34a", linestyle="--", linewidth=1, alpha=0.85, label=f"Target {plan.target1:.2f}"
        )
        if plan.target2 is not None:
            ax.axhline(
                plan.target2,
                color="#16a34a",
                linestyle=":",
                linewidth=0.9,
                alpha=0.6,
                label=f"Target2 {plan.target2:.2f}",
            )

    marker_color = "#16a34a" if signal.direction == "bullish" else "#dc2626"
    ax.scatter([signal.timestamp], [signal.breakout_price], color=marker_color, zorder=5, s=45)

    ax.set_title(f"{signal.index_key} · {signal.pattern} ({signal.interval})", fontsize=11)
    ax.legend(loc="upper left", fontsize=6.5, frameon=False, ncol=2)
    ax.tick_params(axis="y", labelsize=8)

    up = (window["Close"] >= window["Open"]).to_numpy()
    vol_colors = np.where(up, "#16a34a", "#dc2626")
    if len(window) > 1:
        bar_width_days = 0.8 * (window.index[1] - window.index[0]).total_seconds() / 86400.0
    else:
        bar_width_days = 0.6
    vol_ax.bar(window.index, window["Volume"], color=vol_colors, width=bar_width_days, alpha=0.75)
    vol_ax.set_ylabel("Volume", fontsize=7)
    vol_ax.tick_params(axis="x", rotation=30, labelsize=7)
    vol_ax.tick_params(axis="y", labelsize=7)

    ts_tag = pd.Timestamp(signal.timestamp).strftime("%Y%m%d_%H%M%S")
    safe_pattern = signal.pattern.lower().replace(" ", "_")
    path = os.path.join(out_dir, f"{signal.index_key}_{safe_pattern}_{ts_tag}.png")
    fig.savefig(path)
    plt.close(fig)
    return path
