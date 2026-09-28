# TradeBuddy API

FastAPI service that wraps the `niftyscout` package (one directory up) with:

- a background thread running the same scan loop as `python -m niftyscout watch`
- a DB (SQLite locally, Postgres in production via `DATABASE_URL`) storing
  every fresh signal, chart image included (as base64)
- a REST API + Server-Sent Events stream for the dashboard in `../frontend`
- a config endpoint so indices/intervals/detectors/poll interval can be
  changed at runtime without redeploying

See [`../DEPLOYMENT.md`](../DEPLOYMENT.md) for deploying this to Railway.

## Local development

Requires **Python 3.11+** (separate from the CLI tool's own 3.9+ support —
this service's dependency versions are tested against 3.11).

```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Then hit `http://localhost:8000/api/health`, or `/docs` for interactive
Swagger UI.

## Endpoints

| Method | Path | What |
|---|---|---|
| GET | `/api/health` | liveness check |
| GET | `/api/status` | market-open state, last/next scan, telegram status |
| GET | `/api/signals` | recent signals (`?limit=&index=&pattern=`), charts inlined |
| GET | `/api/config` | effective config + what indices/detectors are available |
| PUT | `/api/config` | patch indices/intervals/detectors/poll_seconds/only_market_hours |
| POST | `/api/scan` | trigger an immediate scan pass |
| GET | `/api/replay` | run the CLI's historical sanity-check (`?index=&interval=&lookback=&horizon=`) |
| GET | `/api/stream` | SSE stream, pushes each fresh signal as it's found |

## Data model

Two tables (`app/db.py`):
- `signals` — every fresh signal, one row each, chart PNG as base64 text.
- `config_blob` — a single JSON row holding whatever the dashboard's config
  editor has saved, merged over `../config.yaml`'s defaults at read time so
  a redeploy never silently reverts a user's choices.
