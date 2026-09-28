"""
Bridges niftyscout's blocking scan loop into the API service: every fresh
Signal gets written to the DB (chart PNG inlined as base64) and broadcast to
any dashboard listening on the SSE stream. This is the only place the web
service and the CLI-oriented `niftyscout` package touch each other.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import threading
import time
from typing import Any

from niftyscout.data import YFinanceProvider, is_market_open, now_ist
from niftyscout.dedup import SeenStore
from niftyscout.patterns import Signal
from niftyscout.replay import replay, summarize
from niftyscout.scanner import scan_once

from . import config_store, db


class SignalBus:
    """Thread-safe pub/sub so the (synchronous, background-thread) scanner
    can push events to async SSE subscribers running on the main event
    loop."""

    def __init__(self) -> None:
        self._subscribers: list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = []
        self._lock = threading.Lock()

    def subscribe(self, loop: asyncio.AbstractEventLoop) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        with self._lock:
            self._subscribers.append((loop, queue))
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        with self._lock:
            self._subscribers = [(l, q) for (l, q) in self._subscribers if q is not queue]

    def publish(self, event: dict) -> None:
        with self._lock:
            subs = list(self._subscribers)
        for loop, queue in subs:
            try:
                loop.call_soon_threadsafe(queue.put_nowait, event)
            except RuntimeError:
                pass  # loop already closed, subscriber is gone


bus = SignalBus()


class ScannerState:
    def __init__(self) -> None:
        self.last_scan_at = None
        self.last_scan_found: int | None = None
        self.last_error: str | None = None
        self._stop = False
        self._thread: threading.Thread | None = None

    def stop(self) -> bool:
        return self._stop

    def request_stop(self) -> None:
        self._stop = True


state = ScannerState()
_provider = None
_seen: SeenStore | None = None


def _get_provider():
    global _provider
    if _provider is None:
        _provider = YFinanceProvider()
    return _provider


def _get_seen() -> SeenStore:
    global _seen
    if _seen is None:
        config = config_store.get_effective_config()
        path = config.get("alerts", {}).get("seen_store", "data_cache/seen_signals.json")
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        _seen = SeenStore(path)
    return _seen


def _persist_signal(sig: Signal, chart_path: str | None) -> db.SignalRow:
    chart_b64 = None
    if chart_path and os.path.exists(chart_path):
        with open(chart_path, "rb") as f:
            chart_b64 = base64.b64encode(f.read()).decode("ascii")

    row = db.SignalRow(
        timestamp=sig.timestamp.to_pydatetime() if hasattr(sig.timestamp, "to_pydatetime") else sig.timestamp,
        index_key=sig.index_key,
        interval=sig.interval,
        pattern=sig.pattern,
        direction=sig.direction,
        breakout_price=sig.breakout_price,
        level=sig.level,
        confidence=sig.confidence,
        note=sig.note,
        chart_base64=chart_b64,
    )
    saved = db.insert_signal(row)

    bus.publish(
        {
            "type": "signal",
            "data": {
                "id": saved.id,
                "timestamp": saved.timestamp.isoformat(),
                "index_key": saved.index_key,
                "interval": saved.interval,
                "pattern": saved.pattern,
                "direction": saved.direction,
                "breakout_price": saved.breakout_price,
                "level": saved.level,
                "confidence": saved.confidence,
                "note": saved.note,
                "chart_data_uri": f"data:image/png;base64,{chart_b64}" if chart_b64 else None,
            },
        }
    )
    return saved


def run_scan_once() -> list[Signal]:
    config = config_store.get_effective_config()
    provider = _get_provider()
    seen = _get_seen()
    try:
        fresh = scan_once(provider, config, seen, on_signal=_persist_signal)
        state.last_error = None
    except Exception as exc:  # noqa: BLE001
        state.last_error = str(exc)
        fresh = []
    state.last_scan_at = now_ist()
    state.last_scan_found = len(fresh)
    return fresh


def run_replay(index_key: str, interval: str, lookback: str, horizon: int) -> dict[str, Any]:
    config = config_store.get_effective_config()
    provider = _get_provider()
    df = provider.get_bars(index_key, interval=interval, lookback=lookback)
    if df.empty:
        return {"count": 0}
    det_cfg = config.get("detectors", {})
    results = replay(
        df,
        index_key,
        interval,
        horizon_bars=horizon,
        enabled=det_cfg.get("enabled"),
        params=det_cfg.get("params", {}),
    )
    return summarize(results)


def _loop() -> None:
    while not state.stop():
        config = config_store.get_effective_config()
        only_market_hours = config.get("only_market_hours", True)
        poll_seconds = config.get("poll_seconds", 300)
        if not only_market_hours or is_market_open():
            run_scan_once()
        time.sleep(max(30, poll_seconds))


def start_background_scanner() -> None:
    if state._thread is not None:
        return
    state._thread = threading.Thread(target=_loop, daemon=True, name="niftyscout-scanner")
    state._thread.start()
