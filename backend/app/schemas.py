from __future__ import annotations

import datetime as dt
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class SignalOut(BaseModel):
    id: int
    timestamp: dt.datetime
    index_key: str
    interval: str
    pattern: str
    direction: str
    breakout_price: float
    level: float
    confidence: float
    note: str
    chart_data_uri: Optional[str] = None

    model_config = {"from_attributes": True}


class StatusOut(BaseModel):
    market_open: bool
    now_ist: dt.datetime
    last_scan_at: Optional[dt.datetime]
    last_scan_found: Optional[int]
    next_scan_at: Optional[dt.datetime]
    poll_seconds: int
    only_market_hours: bool
    indices: List[str]
    intervals: List[str]
    telegram_configured: bool
    scanner_error: Optional[str] = None


class DetectorParams(BaseModel):
    lookback: Optional[int] = None
    swing_order: Optional[int] = None
    max_range_pct: Optional[float] = None
    flat_slope_pct: Optional[float] = None
    similarity_pct: Optional[float] = None
    shoulder_similarity_pct: Optional[float] = None
    orb_minutes: Optional[int] = None
    confirm_pct: Optional[float] = None


class ConfigOut(BaseModel):
    indices: List[str]
    intervals: List[str]
    poll_seconds: int
    only_market_hours: bool
    detectors_enabled: List[str]
    detectors_params: Dict[str, dict]
    available_indices: List[str]
    available_detectors: List[str]


class ConfigUpdate(BaseModel):
    indices: Optional[List[str]] = None
    intervals: Optional[List[str]] = None
    poll_seconds: Optional[int] = Field(default=None, ge=30, le=3600)
    only_market_hours: Optional[bool] = None
    detectors_enabled: Optional[List[str]] = None
    detectors_params: Optional[Dict[str, dict]] = None


class ScanResult(BaseModel):
    new_signals: int
    signals: List[SignalOut]


class ReplaySummary(BaseModel):
    index_key: str
    interval: str
    horizon_bars: int
    summary: dict
