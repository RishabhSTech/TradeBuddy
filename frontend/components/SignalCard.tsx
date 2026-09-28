"use client";

import { useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  CaretDown,
  CaretUp,
  Minus,
  Target,
  TrendDown,
  TrendUp,
} from "@phosphor-icons/react";
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
            <Stat label="Signal Quality" value={signal.confidence.toFixed(2)} />
            <Stat label="Time" value={formatTime(signal.timestamp)} />
          </div>

          {signal.indicators && <IndicatorChips indicators={signal.indicators} />}

          {signal.plan && <TradeStructure plan={signal.plan} />}

          {signal.analyst_note && (
            <p className="mb-3 text-sm italic text-muted">{signal.analyst_note}</p>
          )}

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

function IndicatorChips({ indicators }: { indicators: NonNullable<Signal["indicators"]> }) {
  const chips: React.ReactNode[] = [];

  if (indicators.rsi14 !== null) {
    const overbought = indicators.rsi14 >= 70;
    const oversold = indicators.rsi14 <= 30;
    chips.push(
      <Chip
        key="rsi"
        tone={overbought ? "bearish" : oversold ? "bullish" : "neutral"}
        label={`RSI ${indicators.rsi14.toFixed(0)}`}
      />
    );
  }

  if (indicators.trend_direction && indicators.trend_direction !== "flat") {
    const up = indicators.trend_direction === "up";
    chips.push(
      <Chip
        key="trend"
        tone={up ? "bullish" : "bearish"}
        icon={up ? <TrendUp size={12} /> : <TrendDown size={12} />}
        label={up ? "Uptrend" : "Downtrend"}
      />
    );
  }

  if (indicators.rel_volume !== null) {
    const hot = indicators.rel_volume >= 1.5;
    chips.push(
      <Chip
        key="vol"
        tone={hot ? "accent" : "neutral"}
        label={`${indicators.rel_volume.toFixed(1)}x avg volume`}
      />
    );
  }

  if (indicators.macd_hist !== null) {
    const positive = indicators.macd_hist >= 0;
    chips.push(
      <Chip
        key="macd"
        tone={positive ? "bullish" : "bearish"}
        icon={<Minus size={12} className={positive ? "rotate-90" : "-rotate-90"} />}
        label="MACD"
      />
    );
  }

  if (chips.length === 0) return null;

  return <div className="mb-3 flex flex-wrap gap-1.5">{chips}</div>;
}

function Chip({
  tone,
  icon,
  label,
}: {
  tone: "bullish" | "bearish" | "neutral" | "accent";
  icon?: React.ReactNode;
  label: string;
}) {
  const toneClasses = {
    bullish: "border-bullish/40 text-bullish",
    bearish: "border-bearish/40 text-bearish",
    neutral: "border-border text-muted",
    accent: "border-accent/40 text-accent",
  }[tone];

  return (
    <span
      className={`flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-mono ${toneClasses}`}
    >
      {icon}
      {label}
    </span>
  );
}

function TradeStructure({ plan }: { plan: NonNullable<Signal["plan"]> }) {
  return (
    <div className="mb-3 rounded-md border border-border bg-background/40 p-3">
      <div className="mb-2 flex items-center gap-1.5 text-[11px] text-muted">
        <Target size={12} />
        Trade structure ({plan.method.replace(/_/g, " ")})
      </div>
      <div className="grid grid-cols-2 gap-3 font-mono text-sm sm:grid-cols-4">
        <Stat label="Entry" value={plan.entry.toFixed(2)} />
        <Stat label="Stop" value={plan.stop.toFixed(2)} />
        <Stat label="Target 1" value={`${plan.target1.toFixed(2)} (${plan.r_multiple_1.toFixed(1)}R)`} />
        {plan.target2 !== null && plan.r_multiple_2 !== null ? (
          <Stat label="Target 2" value={`${plan.target2.toFixed(2)} (${plan.r_multiple_2.toFixed(1)}R)`} />
        ) : (
          <Stat label="Target 2" value="-" />
        )}
      </div>
    </div>
  );
}
