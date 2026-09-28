"use client";

import { useState } from "react";
import { ArrowDown, ArrowUp, CaretDown, CaretUp } from "@phosphor-icons/react";
import type { Signal } from "@/lib/types";

function formatTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function SignalCard({ signal, isNew }: { signal: Signal; isNew?: boolean }) {
  const [open, setOpen] = useState(false);
  const bullish = signal.direction === "bullish";

  return (
    <div
      className={`rounded-lg border border-border bg-surface transition-colors ${
        isNew ? "border-accent/60" : ""
      }`}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left"
      >
        <span
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${
            bullish ? "bg-bullish/10 text-bullish" : "bg-bearish/10 text-bearish"
          }`}
        >
          {bullish ? <ArrowUp size={16} weight="bold" /> : <ArrowDown size={16} weight="bold" />}
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline gap-x-2">
            <span className="font-medium text-foreground">{signal.index_key}</span>
            <span className="text-sm text-muted">{signal.interval}</span>
            <span className="text-sm text-foreground/90">{signal.pattern}</span>
          </div>
          <p className="truncate text-sm text-muted">{signal.note}</p>
        </div>

        <div className="hidden shrink-0 text-right sm:block">
          <div className="font-mono text-sm text-foreground">
            {signal.breakout_price.toFixed(2)}
          </div>
          <div className="text-xs text-muted">{formatTime(signal.timestamp)}</div>
        </div>

        <span className="shrink-0 text-muted">
          {open ? <CaretUp size={16} /> : <CaretDown size={16} />}
        </span>
      </button>

      {open && (
        <div className="border-t border-border px-4 py-4">
          <div className="mb-3 grid grid-cols-2 gap-3 font-mono text-sm sm:grid-cols-4">
            <Stat label="Price" value={signal.breakout_price.toFixed(2)} />
            <Stat label="Level" value={signal.level.toFixed(2)} />
            <Stat label="Confidence" value={signal.confidence.toFixed(2)} />
            <Stat label="Time" value={formatTime(signal.timestamp)} />
          </div>
          {signal.chart_data_uri ? (
            // eslint-disable-next-line @next/next/no-img-element -- inline base64 data URI, nothing for next/image to optimize
            <img
              src={signal.chart_data_uri}
              alt={`${signal.index_key} ${signal.pattern} chart`}
              className="w-full rounded-md border border-border"
            />
          ) : (
            <p className="text-sm text-muted">No chart was rendered for this signal.</p>
          )}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[11px] text-muted">{label}</div>
      <div className="text-foreground">{value}</div>
    </div>
  );
}
