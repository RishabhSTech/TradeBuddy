# TradeBuddy dashboard

Next.js dashboard for [TradeBuddy](../README.md): a live signal feed, config
editor, and a lightweight replay/backtest panel, talking to the FastAPI
backend in [`../backend`](../backend).

## Local development

```bash
npm install
cp .env.example .env.local   # point NEXT_PUBLIC_API_BASE_URL at your backend
npm run dev
```

Open http://localhost:3000. The backend must be running separately (see
`../backend`) or you'll see a "could not reach the API" banner instead of
data.

## Deploying

See [`../DEPLOYMENT.md`](../DEPLOYMENT.md) for the full Railway + Vercel
setup. In short: import this repo into Vercel, set the project's **Root
Directory** to `frontend`, and set `NEXT_PUBLIC_API_BASE_URL` to your Railway
backend's public URL.
