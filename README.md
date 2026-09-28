# NiftyScout

An alert-only pattern-breakout watcher for **Nifty 50, Bank Nifty and Sensex**.
It never places an order. It watches price, recognizes chart-pattern
breakouts, and tells you: *"Boss, we might have a trade!"* — with a chart
attached — so you can decide for yourself.

## What it watches for

| Pattern | Signal fires when... |
|---|---|
| Range breakout / breakdown | Price has been consolidating tightly, then closes clearly outside that range |
| Ascending / descending / symmetrical triangle | Swing highs/lows are converging into a triangle, and price closes through the trendline |
| Double top / double bottom | Two similar peaks (or troughs) form, and price breaks the neckline between them |
| Head and shoulders / inverse H&S | Three peaks (or troughs) with a taller middle one, and price breaks the neckline |
| Opening range breakout (ORB) | Price breaks above/below the first 15 minutes' range on the day — the classic index day-trade setup |

All of it runs on **Nifty (`^NSEI`), Bank Nifty (`^NSEBANK`) and Sensex
(`^BSESN`)** by default (see `niftyscout/symbols.py`).

## Quick start

```bash
pip install -r requirements.txt

# one-off check right now
python -m niftyscout scan

# keep watching during market hours (9:15-15:30 IST, Mon-Fri)
python -m niftyscout watch

# sanity-check a pattern against history (not a real backtest, see below)
python -m niftyscout replay --index NIFTY --interval 1d --lookback 2y --horizon 10
```

Everything is tunable in `config.yaml` — which indices, which timeframes,
which patterns, and how strict each one is (range tightness, similarity
tolerance, breakout confirmation margin, etc).

## Getting alerts on your phone (Telegram)

1. Message **@BotFather** on Telegram, send `/newbot`, and copy the token it
   gives you.
2. Message your new bot once (anything), then visit
   `https://api.telegram.org/bot<TOKEN>/getUpdates` and read your `chat.id`
   out of the JSON.
3. Set two environment variables before running `watch`:
   ```bash
   export NIFTYSCOUT_TG_TOKEN="123456:ABC-your-token"
   export NIFTYSCOUT_TG_CHAT_ID="123456789"
   ```
4. That's it — every alert now also lands in Telegram with the chart image
   attached. No Telegram configured? It still prints to the console.

## Where the price data comes from

By default, `YFinanceProvider` pulls from Yahoo Finance — free, but usually
**15-20 minutes delayed**. That's fine for spotting a pattern and getting a
heads-up; it is *not* the same as your broker's live tick feed. If you want
alerts within seconds of a real breakout, swap in your broker's WebSocket
feed (Kite Connect, Angel One SmartAPI, Dhan, Upstox, Fyers all have one) by
writing a small class that implements `DataProvider.get_bars(...)` in
`niftyscout/data.py` — nothing else in the codebase needs to change.

There's also a `CSVProvider` for testing against your own exported history:
```bash
python -m niftyscout --csv NIFTY=my_nifty_15m.csv,BANKNIFTY=my_bn_15m.csv scan
```

## Running unattended (so it's actually watching while you're not)

`watch` is a long-running loop, so run it under something that keeps it
alive and restarts it if it dies:

- **Simplest**: `nohup python -m niftyscout watch &` inside a `tmux`/`screen` session on a small VPS.
- **systemd** (Linux server): a unit file that runs `python -m niftyscout watch` with `Restart=always`.
- **cron**: instead of `watch`, schedule `python -m niftyscout scan` every 5 minutes during market hours — the dedup store (`data_cache/seen_signals.json`) makes repeated `scan` calls safe, so this is a perfectly good alternative to a long-running loop.

## On regulation (SEBI, 2026)

This tool only reads market data and sends you a notification — it never
places, modifies or cancels an order, so it sits outside SEBI's retail algo
framework (which governs *order placement* via API, Algo-IDs, and static-IP
whitelisting). The moment you connect this to a broker API to place orders
automatically — for yourself or, especially, for other people — those rules
apply to you, and for anyone else's money you'd also be stepping into
principal-agent/Research-Analyst territory. Keep this tool as "tell me,
I'll decide" and you stay clear of that.

## About `replay` — read this before trusting a hit rate

`replay` is a sanity check, not a backtest. It has no transaction costs, no
slippage, no realistic stop-loss/target logic — it just asks "N bars after
this signal, was price higher (for a bullish signal) or lower (for a
bearish one)?" Use it to get a rough feel for whether a pattern setup is
worth watching on a given index/timeframe, not as proof a strategy works.
Markets change; a good hit rate on 2024-2025 data is not a promise for
tomorrow.

## Project layout

```
niftyscout/
  symbols.py    index -> ticker map (Nifty/Bank Nifty/Sensex)
  data.py       DataProvider interface + YFinance/CSV implementations
  swings.py     swing high/low detection (used by triangle/double/H&S)
  patterns.py   the 5 pattern detectors + Signal dataclass
  chart.py      renders a PNG for a signal
  alerts.py     console + Telegram dispatch
  dedup.py      disk-backed "don't repeat this alert" store
  scanner.py    the scan-once / watch-loop orchestration (+ an on_signal hook the API uses)
  replay.py     lightweight historical sanity-check
  cli.py        `scan` / `watch` / `replay` commands
backend/        FastAPI service wrapping the package above: DB-backed signal
                history, a background scanner, and a REST + SSE API for the
                dashboard. See backend/README or DEPLOYMENT.md.
frontend/       Next.js dashboard (live signal feed, config editor, replay
                panel) that talks to the backend. See frontend/README.md.
tests/
  synth.py           synthetic OHLCV generators with known patterns baked in
  test_patterns.py   unit tests for every detector
config.yaml     all the tunables (shipped defaults; the dashboard's config
                editor overrides these at runtime without editing this file)
```

## Dashboard (optional) — a UI, deployed automatically

The CLI above is the whole tool; everything in `backend/` and `frontend/` is
an optional layer on top for people who want a live web dashboard instead of
(or alongside) the terminal/Telegram alerts:

- **`backend/`** — a FastAPI service that runs the same scan loop as `watch`,
  but persists every signal (with its chart) to a database and exposes it
  over a REST API + a live SSE stream, plus a config endpoint so indices/
  detectors/poll interval can be changed from a browser instead of editing
  `config.yaml`.
- **`frontend/`** — a Next.js dashboard: a live signal feed, a config
  editor, and a "replay" panel for the historical sanity-check.

**[See DEPLOYMENT.md](DEPLOYMENT.md)** for the full setup: push to GitHub,
deploy the backend to Railway, deploy the dashboard to Vercel. Once both are
connected to the repo, every `git push` redeploys both automatically.

## Disclaimer

This is a decision-support tool, not investment advice, and it does not
guarantee any outcome. Nifty, Bank Nifty and Sensex derivatives are
leveraged, fast-moving instruments — the large majority of retail F&O
traders lose money. Please size positions and manage risk yourself; nothing
here does that for you.
