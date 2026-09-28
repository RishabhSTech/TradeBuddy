# Deploying TradeBuddy: backend on Railway, dashboard on Vercel

This repo has three parts:

```
niftyscout/     the original CLI scanning engine (unchanged)
backend/        FastAPI service that wraps niftyscout, adds a DB + scheduler + REST/SSE API
frontend/       Next.js dashboard that talks to the backend
```

The backend runs the scan loop continuously and persists signal history to a
database. The frontend is a static-ish Next.js app that just calls the
backend's API. Once both are pushed to GitHub, Railway and Vercel each watch
the repo and redeploy automatically on every push to `main` — that's "the
automation."

## 0. Push to GitHub

Railway and Vercel both deploy from a GitHub repo, so this has to happen first.

```bash
cd nifty-breakout-scout
git add -A
git commit -m "Add API backend, dashboard, and deploy config"

# create an empty repo named TradeBuddy on github.com, then:
git remote add origin git@github.com:<you>/TradeBuddy.git
git push -u origin main
# (or, with the gh CLI installed and authenticated: gh repo create TradeBuddy --private --source=. --remote=origin --push)
```

## 1. Backend -> Railway

1. On [railway.app](https://railway.app), **New Project -> Deploy from GitHub repo** -> pick this repo.
2. Railway will detect `Dockerfile` and `railway.json` at the repo root and build from there automatically. **Do not set a Root Directory** for this service — the Dockerfile needs both `niftyscout/` and `backend/` from the repo root to build.
3. **Add a Postgres database**: in the same project, **New -> Database -> Add PostgreSQL**. Railway automatically injects `DATABASE_URL` into every service in the project, including this one — nothing else to configure. (Without this, the backend falls back to a local SQLite file that's wiped on every redeploy.)
4. Set these **Variables** on the backend service:
   | Variable | Value |
   |---|---|
   | `FRONTEND_ORIGIN` | your Vercel URL, e.g. `https://tradebuddy.vercel.app` (comma-separate if you have more than one, e.g. also a preview URL) |
   | `NIFTYSCOUT_TG_TOKEN` | *(optional)* Telegram bot token, if you want Telegram alerts too |
   | `NIFTYSCOUT_TG_CHAT_ID` | *(optional)* Telegram chat id |
5. Deploy. Railway gives the service a public URL under **Settings -> Networking -> Generate Domain** (something like `tradebuddy-backend.up.railway.app`). Copy it — the frontend needs it.
6. Sanity check: `curl https://<your-backend>.up.railway.app/api/health` should return `{"ok":true}`.

The backend starts scanning on its own as soon as it boots (a background thread, same scan-once logic as the CLI's `watch` loop, gated by `only_market_hours` and `poll_seconds` from `config.yaml` / whatever you've since changed from the dashboard).

## 2. Frontend -> Vercel

1. On [vercel.com](https://vercel.com), **Add New -> Project** -> import the same GitHub repo.
2. In the import screen (or afterwards under **Settings -> General**), set **Root Directory** to `frontend`. This is the one manual setting Vercel needs for a monorepo — everything else (Next.js build command, output dir) is auto-detected.
3. Add an environment variable:
   | Variable | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE_URL` | your Railway backend URL from step 1, e.g. `https://tradebuddy-backend.up.railway.app` (no trailing slash) |
4. Deploy. Vercel gives you a `https://<project>.vercel.app` URL.
5. Go back to Railway and set `FRONTEND_ORIGIN` (step 1.4) to this exact URL if you hadn't yet, then redeploy the backend so CORS allows it.

## 3. Confirm the automation loop

From here on:
- `git push` to `main` → Railway rebuilds and redeploys the backend, Vercel rebuilds and redeploys the frontend. Both automatically, no manual trigger.
- Open a PR → Vercel builds a preview deployment per-PR automatically (Railway can be configured to do the same via **PR Environments** in project settings, if you want a full staging backend per PR too).

## Local development

Backend (needs Python 3.11+; the CLI tool itself supports 3.9+, but the API's dependency pins are tested on 3.11):

```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
```

Open http://localhost:3000.

## What the dashboard shows

- **Signals** — live feed of every fresh breakout the scanner has found, with the chart image, filterable by index. New signals pushed live over SSE while the tab is open.
- **Config** — pick indices/intervals/detectors, poll interval, market-hours gating. Saves to the backend's DB so it survives redeploys, without touching the checked-in `config.yaml` defaults.
- **Replay** — the CLI's `replay` sanity-check, from the browser: pick an index/interval/lookback/horizon and see hit-rate-by-pattern. Still not a backtest — see the root README's caveats.

## Notes on cost and persistence

- Railway's free/hobby tier and a Postgres addon are enough for this; the workload is light (a scan every few minutes, small DB rows).
- Chart images are stored as base64 inside the DB rows (not on disk), specifically so a Railway redeploy or restart never loses them and no separate object storage/CDN is needed.
- The CLI (`python -m niftyscout scan|watch|replay`) still works exactly as before and is untouched by any of this — the backend is an additive layer, not a replacement.
