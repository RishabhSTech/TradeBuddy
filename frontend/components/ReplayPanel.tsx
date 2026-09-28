"use client";

import { useState } from "react";
import { ChartLineUp, CircleNotch } from "@phosphor-icons/react";
import { api, ApiError } from "@/lib/api";
import type { Config, ReplaySummary } from "@/lib/types";

export function ReplayPanel({ config }: { config: Config }) {
  const [index, setIndex] = useState(config.available_indices[0] ?? "NIFTY");
  const [interval, setInterval_] = useState("1d");
  const [lookback, setLookback] = useState("2y");
  const [horizon, setHorizon] = useState(10);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ReplaySummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.replay({ index, interval, lookback, horizon });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Replay failed. Is the backend reachable?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4 rounded-lg border border-border bg-surface p-4">
      <p className="text-sm text-muted">
        Sanity check, not a backtest: for each historical signal, did price move the signalled
        direction within the horizon?
      </p>

      <div className="flex flex-wrap items-end gap-3">
        <Field label="Index">
          <select
            value={index}
            onChange={(e) => setIndex(e.target.value)}
            className="rounded-md border border-border bg-background px-2.5 py-1.5 text-sm text-foreground focus:border-accent focus:outline-none"
          >
            {config.available_indices.map((idx) => (
              <option key={idx} value={idx}>
                {idx}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Interval">
          <select
            value={interval}
            onChange={(e) => setInterval_(e.target.value)}
            className="rounded-md border border-border bg-background px-2.5 py-1.5 text-sm text-foreground focus:border-accent focus:outline-none"
          >
            {["15m", "1h", "1d"].map((iv) => (
              <option key={iv} value={iv}>
                {iv}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Lookback">
          <select
            value={lookback}
            onChange={(e) => setLookback(e.target.value)}
            className="rounded-md border border-border bg-background px-2.5 py-1.5 text-sm text-foreground focus:border-accent focus:outline-none"
          >
            {["1mo", "3mo", "1y", "2y"].map((lb) => (
              <option key={lb} value={lb}>
                {lb}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Horizon (bars)">
          <input
            type="number"
            min={1}
            max={100}
            value={horizon}
            onChange={(e) => setHorizon(Number(e.target.value))}
            className="w-24 rounded-md border border-border bg-background px-2.5 py-1.5 text-sm font-mono text-foreground focus:border-accent focus:outline-none"
          />
        </Field>

        <button
          onClick={run}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-md border border-accent px-3 py-1.5 text-sm font-medium text-accent transition-transform active:scale-[0.98] disabled:opacity-60"
        >
          {loading ? <CircleNotch size={14} className="animate-spin" /> : <ChartLineUp size={14} weight="bold" />}
          Run
        </button>
      </div>

      {error && <p className="text-sm text-bearish">{error}</p>}

      {result && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted">
                <th className="py-1.5 pr-4 font-normal">Pattern</th>
                <th className="py-1.5 pr-4 font-normal">Signals</th>
                <th className="py-1.5 pr-4 font-normal">Hit rate</th>
                <th className="py-1.5 pr-4 font-normal">Avg forward return</th>
              </tr>
            </thead>
            <tbody>
              {result.summary.count === 0 || !result.summary.patterns ? (
                <tr>
                  <td colSpan={4} className="py-3 text-muted">
                    No signals found for this window.
                  </td>
                </tr>
              ) : (
                Object.entries(result.summary.patterns).map(([pattern, stats]) => (
                  <tr key={pattern} className="border-b border-border/60 font-mono">
                    <td className="py-1.5 pr-4 font-sans text-foreground">{pattern}</td>
                    <td className="py-1.5 pr-4 text-foreground">{stats.signals}</td>
                    <td
                      className={`py-1.5 pr-4 ${
                        stats.hit_rate_pct >= 50 ? "text-bullish" : "text-bearish"
                      }`}
                    >
                      {stats.hit_rate_pct}%
                    </td>
                    <td className="py-1.5 pr-4 text-foreground">
                      {stats.avg_forward_return_pct}%
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5 text-sm">
      <span className="text-muted">{label}</span>
      {children}
    </label>
  );
}
