"""
Renders a quick chart PNG for a signal: price line, the broken level, and a
marker at the breakout bar. Sent alongside Telegram alerts so you can eyeball
the pattern before deciding anything.
"""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

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

    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=130)
    ax.plot(window.index, window["Close"], color="#2563eb", linewidth=1.4, label="Close")
    ax.axhline(signal.level, color="#94a3b8", linestyle="--", linewidth=1, label=f"Level {signal.level:.2f}")

    color = "#16a34a" if signal.direction == "bullish" else "#dc2626"
    ax.scatter([signal.timestamp], [signal.breakout_price], color=color, zorder=5, s=45)

    ax.set_title(f"{signal.index_key} · {signal.pattern} ({signal.interval})", fontsize=11)
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    ax.tick_params(axis="x", rotation=30, labelsize=7)
    ax.tick_params(axis="y", labelsize=8)
    fig.tight_layout()

    ts_tag = pd.Timestamp(signal.timestamp).strftime("%Y%m%d_%H%M%S")
    safe_pattern = signal.pattern.lower().replace(" ", "_")
    path = os.path.join(out_dir, f"{signal.index_key}_{safe_pattern}_{ts_tag}.png")
    fig.savefig(path)
    plt.close(fig)
    return path
