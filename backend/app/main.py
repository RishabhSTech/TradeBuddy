"""
TradeBuddy API — a thin FastAPI service around the niftyscout package.

Endpoints:
    GET  /api/health           liveness check
    GET  /api/status           market-open state, last/next scan, telegram status
    GET  /api/signals          recent signals (with chart images inlined)
    GET  /api/config           effective config + what's available to pick from
    PUT  /api/config           patch indices/intervals/detectors/poll_seconds
    POST /api/scan             trigger an immediate scan pass
    GET  /api/replay           run the lightweight historical sanity-check
    GET  /api/stream           Server-Sent Events: pushes each fresh signal live
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from niftyscout.alerts import telegram_configured
from niftyscout.data import is_market_open, now_ist
from niftyscout.patterns import DETECTORS
from niftyscout.symbols import DEFAULT_KEYS

from . import config_store, db, runner
from .schemas import (
    ConfigOut,
    ConfigUpdate,
    ReplaySummary,
    ScanResult,
    SignalOut,
    StatusOut,
)

app = FastAPI(title="TradeBuddy API", version="1.0.0")

_origins = os.environ.get("FRONTEND_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _origins == "*" else [o.strip() for o in _origins.split(",")],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    db.init_db()
    runner.start_background_scanner()


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


def _row_to_signal_out(row: db.SignalRow) -> SignalOut:
    chart_uri = f"data:image/png;base64,{row.chart_base64}" if row.chart_base64 else None
    return SignalOut(
        id=row.id,
        timestamp=row.timestamp,
        index_key=row.index_key,
        interval=row.interval,
        pattern=row.pattern,
        direction=row.direction,
        breakout_price=row.breakout_price,
        level=row.level,
        confidence=row.confidence,
        note=row.note,
        chart_data_uri=chart_uri,
        pattern_height=row.pattern_height,
        confidence_breakdown=row.confidence_breakdown,
        indicators=row.indicators,
        volume_levels=row.volume_levels,
        plan=row.plan,
        analyst_note=row.analyst_note,
    )


@app.get("/api/status", response_model=StatusOut)
def status() -> StatusOut:
    config = config_store.get_effective_config()
    poll_seconds = config.get("poll_seconds", 300)
    next_scan_at = None
    if runner.state.last_scan_at is not None:
        next_scan_at = runner.state.last_scan_at + dt.timedelta(seconds=poll_seconds)
    return StatusOut(
        market_open=is_market_open(),
        now_ist=now_ist(),
        last_scan_at=runner.state.last_scan_at,
        last_scan_found=runner.state.last_scan_found,
        next_scan_at=next_scan_at,
        poll_seconds=poll_seconds,
        only_market_hours=config.get("only_market_hours", True),
        indices=config.get("indices", []),
        intervals=config.get("intervals", []),
        telegram_configured=telegram_configured(),
        scanner_error=runner.state.last_error,
    )


@app.get("/api/signals", response_model=List[SignalOut])
def get_signals(
    limit: int = Query(default=100, ge=1, le=500),
    index: Optional[str] = Query(default=None),
    pattern: Optional[str] = Query(default=None),
) -> List[SignalOut]:
    rows = db.list_signals(limit=limit, index_key=index, pattern=pattern)
    return [_row_to_signal_out(r) for r in rows]


@app.get("/api/config", response_model=ConfigOut)
def get_config() -> ConfigOut:
    config = config_store.get_effective_config()
    det = config.get("detectors", {})
    return ConfigOut(
        indices=config.get("indices", []),
        intervals=config.get("intervals", []),
        poll_seconds=config.get("poll_seconds", 300),
        only_market_hours=config.get("only_market_hours", True),
        detectors_enabled=det.get("enabled", []),
        detectors_params=det.get("params", {}),
        indicator_params=config.get("indicators", {}),
        level_params=config.get("levels", {}),
        volume_profile_params=config.get("volume_profile", {}),
        available_indices=DEFAULT_KEYS,
        available_detectors=list(DETECTORS.keys()),
    )


@app.put("/api/config", response_model=ConfigOut)
def update_config(patch: ConfigUpdate) -> ConfigOut:
    data = patch.model_dump(exclude_none=True)

    for idx in data.get("indices", []):
        if idx not in DEFAULT_KEYS:
            raise HTTPException(400, f"Unknown index '{idx}'. Choose from {DEFAULT_KEYS}.")
    for name in data.get("detectors_enabled", []):
        if name not in DETECTORS:
            raise HTTPException(400, f"Unknown detector '{name}'. Choose from {list(DETECTORS)}.")

    config_store.save_overrides(data)
    return get_config()


@app.post("/api/scan", response_model=ScanResult)
async def trigger_scan() -> ScanResult:
    fresh = await run_in_threadpool(runner.run_scan_once)
    rows = db.list_signals(limit=len(fresh)) if fresh else []
    return ScanResult(new_signals=len(fresh), signals=[_row_to_signal_out(r) for r in rows])


@app.get("/api/replay", response_model=ReplaySummary)
async def get_replay(
    index: str = Query(default="NIFTY"),
    interval: str = Query(default="1d"),
    lookback: str = Query(default="2y"),
    horizon: int = Query(default=10, ge=1, le=100),
) -> ReplaySummary:
    if index not in DEFAULT_KEYS:
        raise HTTPException(400, f"Unknown index '{index}'. Choose from {DEFAULT_KEYS}.")
    summary = await run_in_threadpool(runner.run_replay, index, interval, lookback, horizon)
    return ReplaySummary(index_key=index, interval=interval, horizon_bars=horizon, summary=summary)


@app.get("/api/stream")
async def stream():
    loop = asyncio.get_event_loop()
    queue = runner.bus.subscribe(loop)

    async def event_generator():
        try:
            yield {"event": "connected", "data": json.dumps({"ok": True})}
            while True:
                event = await queue.get()
                yield {"event": event["type"], "data": json.dumps(event["data"])}
        finally:
            runner.bus.unsubscribe(queue)

    return EventSourceResponse(event_generator())
