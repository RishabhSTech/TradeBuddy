"""
A tiny disk-backed set so the scanner doesn't ping you twenty times about
the same breakout every time it re-scans. Keyed on index + pattern +
direction + rounded level + rounded timestamp (to the minute), persisted as
JSON so it survives restarts.
"""

from __future__ import annotations

import json
import os

from .patterns import Signal


class SeenStore:
    def __init__(self, path: str = "data_cache/seen_signals.json"):
        self.path = path
        self._seen: set[str] = set()
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                self._seen = set(json.load(f))

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(sorted(self._seen), f)

    @staticmethod
    def _key(signal: Signal) -> str:
        ts = str(signal.timestamp)[:16]  # minute resolution
        return f"{signal.index_key}|{signal.interval}|{signal.pattern}|{signal.direction}|{round(signal.level, 1)}|{ts}"

    def is_new(self, signal: Signal) -> bool:
        return self._key(signal) not in self._seen

    def mark(self, signal: Signal) -> None:
        self._seen.add(self._key(signal))
        self._save()
