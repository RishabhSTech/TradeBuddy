"""
Merges the repo's checked-in config.yaml (shipped defaults) with runtime
overrides saved to the DB by the dashboard's config editor, so a redeploy
never silently discards a user's choices about which indices/detectors to
watch.
"""

from __future__ import annotations

import copy
import os
import threading

import yaml

from . import db

CONFIG_YAML_PATH = os.environ.get(
    "NIFTYSCOUT_CONFIG_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "config.yaml"),
)

_lock = threading.Lock()


def _load_defaults() -> dict:
    with open(CONFIG_YAML_PATH, "r") as f:
        return yaml.safe_load(f)


def get_effective_config() -> dict:
    """Defaults from config.yaml, shallow-overridden by whatever the
    dashboard has saved to the DB (indices/intervals/poll/detectors)."""
    with _lock:
        config = _load_defaults()
        override = db.get_config_override() or {}

        if "indices" in override:
            config["indices"] = override["indices"]
        if "intervals" in override:
            config["intervals"] = override["intervals"]
        if "poll_seconds" in override:
            config["poll_seconds"] = override["poll_seconds"]
        if "only_market_hours" in override:
            config["only_market_hours"] = override["only_market_hours"]

        detectors = copy.deepcopy(config.get("detectors", {}))
        if "detectors_enabled" in override:
            detectors["enabled"] = override["detectors_enabled"]
        if "detectors_params" in override:
            params = detectors.setdefault("params", {})
            for name, values in override["detectors_params"].items():
                params.setdefault(name, {}).update(values)
        config["detectors"] = detectors

        return config


def save_overrides(patch: dict) -> dict:
    """Merges `patch` (already-validated ConfigUpdate.dict(exclude_none=True))
    into the stored override blob and persists it."""
    with _lock:
        current = db.get_config_override() or {}
        current.update(patch)
        if "detectors_params" in patch:
            merged_params = dict(current.get("detectors_params", {}))
            for name, values in patch["detectors_params"].items():
                merged_params.setdefault(name, {}).update(values)
            current["detectors_params"] = merged_params
        db.save_config_override(current)
    return get_effective_config()
