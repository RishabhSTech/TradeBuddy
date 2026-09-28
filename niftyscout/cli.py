"""
Command-line entry point.

    python -m niftyscout scan               # one pass, print/alert on new signals
    python -m niftyscout watch               # loop during market hours
    python -m niftyscout replay --index NIFTY --interval 1d --lookback 2y
"""

from __future__ import annotations

import argparse
import json

import yaml

from .data import CSVProvider, YFinanceProvider
from .dedup import SeenStore
from .replay import replay, summarize
from .scanner import scan_once, watch_loop


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def build_provider(args, config: dict):
    if getattr(args, "csv", None):
        # expects e.g. --csv NIFTY=nifty.csv,BANKNIFTY=banknifty.csv
        paths = dict(pair.split("=", 1) for pair in args.csv.split(","))
        return CSVProvider(paths)
    return YFinanceProvider()


def cmd_scan(args):
    config = load_config(args.config)
    provider = build_provider(args, config)
    seen = SeenStore(config.get("alerts", {}).get("seen_store", "data_cache/seen_signals.json"))
    fresh = scan_once(provider, config, seen)
    print(f"\n{len(fresh)} new signal(s) this pass.")


def cmd_watch(args):
    config = load_config(args.config)
    provider = build_provider(args, config)
    watch_loop(provider, config)


def cmd_replay(args):
    config = load_config(args.config)
    provider = build_provider(args, config)
    df = provider.get_bars(args.index, interval=args.interval, lookback=args.lookback)
    if df.empty:
        print("No data returned for that index/interval/lookback.")
        return
    det_cfg = config.get("detectors", {})
    results = replay(
        df,
        args.index,
        args.interval,
        horizon_bars=args.horizon,
        enabled=det_cfg.get("enabled"),
        params=det_cfg.get("params", {}),
    )
    print(json.dumps(summarize(results), indent=2))
    if args.verbose:
        for r in results:
            print(
                f"{r.signal.timestamp} {r.signal.index_key} {r.signal.pattern} "
                f"({r.signal.direction}) -> {r.forward_return_pct}% "
                f"{'HIT' if r.hit else 'miss'}"
            )


def main():
    parser = argparse.ArgumentParser(prog="niftyscout")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument(
        "--csv", default=None,
        help="Use local CSV files instead of live data, e.g. NIFTY=nifty.csv,SENSEX=sensex.csv",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("scan", help="Run one scan pass and alert on new signals")
    sub.add_parser("watch", help="Loop and alert during market hours")

    p_replay = sub.add_parser("replay", help="Backtest-lite: replay detectors on history")
    p_replay.add_argument("--index", default="NIFTY")
    p_replay.add_argument("--interval", default="1d")
    p_replay.add_argument("--lookback", default="2y")
    p_replay.add_argument("--horizon", type=int, default=10, help="bars ahead to check outcome")
    p_replay.add_argument("--verbose", action="store_true")

    args = parser.parse_args()
    {
        "scan": cmd_scan,
        "watch": cmd_watch,
        "replay": cmd_replay,
    }[args.command](args)


if __name__ == "__main__":
    main()
