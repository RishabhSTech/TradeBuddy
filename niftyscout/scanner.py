"""
The watch loop: pull bars for each configured index/interval, run the
detectors, and dispatch an alert for anything new on (or near) the latest
bar. This is the only place that decides "is this signal fresh enough to
tell the boss about" — detectors themselves are stateless and happily
re-report the same historical breakout every time they're called.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from .alerts import dispatch
from .chart import render_signal_chart
from .data import DataProvider, is_market_open, now_ist
from .dedup import SeenStore
from .patterns import Signal, detect_all

OnSignal = Callable[[Signal, "str | None"], None]


def scan_once(
    provider: DataProvider,
    config: dict[str, Any],
    seen: SeenStore,
    recent_bars: int = 2,
    on_signal: OnSignal | None = None,
) -> list[Signal]:
    """Runs one pass over every configured index x interval, returns the
    NEW signals it found (and has already dispatched)."""
    fresh: list[Signal] = []
    indices = config.get("indices", [])
    intervals = config.get("intervals", [])
    lookback_map = config.get("lookback", {})
    det_cfg = config.get("detectors", {})
    enabled = det_cfg.get("enabled")
    params = det_cfg.get("params", {})
    alert_cfg = config.get("alerts", {})
    indicator_params = config.get("indicators", {})
    level_params = config.get("levels", {})
    volume_profile_params = config.get("volume_profile", {})

    for index_key in indices:
        for interval in intervals:
            lookback = lookback_map.get(interval, "1mo")
            try:
                df = provider.get_bars(index_key, interval=interval, lookback=lookback)
            except Exception as exc:  # noqa: BLE001 - keep scanning other symbols
                print(f"[scanner] failed to fetch {index_key} {interval}: {exc}")
                continue
            if df.empty or len(df) < 5:
                continue

            signals = detect_all(
                df,
                index_key,
                interval,
                enabled=enabled,
                params=params,
                indicator_params=indicator_params,
                level_params=level_params,
                volume_profile_params=dict(volume_profile_params),
            )
            if not signals:
                continue

            cutoff = df.index[-recent_bars]
            for sig in signals:
                if sig.timestamp < cutoff:
                    continue
                if not seen.is_new(sig):
                    continue
                chart_path = None
                if alert_cfg.get("send_chart", True):
                    try:
                        chart_path = render_signal_chart(
                            df, sig, out_dir=alert_cfg.get("charts_dir", "charts")
                        )
                    except Exception as exc:  # noqa: BLE001
                        print(f"[scanner] chart render failed: {exc}")
                dispatch(sig, chart_path=chart_path)
                seen.mark(sig)
                fresh.append(sig)
                if on_signal is not None:
                    try:
                        on_signal(sig, chart_path)
                    except Exception as exc:  # noqa: BLE001 - a bad hook can't kill the scan
                        print(f"[scanner] on_signal hook failed: {exc}")
    return fresh


def watch_loop(
    provider: DataProvider,
    config: dict[str, Any],
    on_signal: OnSignal | None = None,
    stop: Callable[[], bool] | None = None,
) -> None:
    seen = SeenStore(config.get("alerts", {}).get("seen_store", "data_cache/seen_signals.json"))
    poll_seconds = config.get("poll_seconds", 300)
    only_market_hours = config.get("only_market_hours", True)

    print("NiftyScout watching:", ", ".join(config.get("indices", [])))
    while stop is None or not stop():
        if only_market_hours and not is_market_open():
            print(f"[{now_ist():%H:%M:%S}] market closed, sleeping...")
        else:
            fresh = scan_once(provider, config, seen, on_signal=on_signal)
            if not fresh:
                print(f"[{now_ist():%H:%M:%S}] scanned, nothing new")
        time.sleep(poll_seconds)
