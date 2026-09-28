"use client";

import { ArrowsClockwise, CircleNotch, WarningCircle, WifiHigh, WifiSlash } from "@phosphor-icons/react";
import type { Status } from "@/lib/types";

function formatClock(iso: string | null) {
  if (!iso) return "never";
  return new Date(iso).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

export function StatusBar({
  status,
  connected,
  scanning,
  onScan,
}: {
  status: Status | null;
  connected: boolean;
  scanning: boolean;
  onScan: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-lg border border-border bg-surface px-4 py-3">
      <div className="flex items-center gap-2">
        <span
          className={`h-2 w-2 rounded-full ${
            status?.market_open ? "bg-bullish" : "bg-muted"
          }`}
        />
        <span className="text-sm text-foreground">
          {status?.market_open ? "Market open" : "Market closed"}
        </span>
      </div>

      <Metric label="Last scan" value={formatClock(status?.last_scan_at ?? null)} />
      <Metric label="Poll every" value={status ? `${status.poll_seconds}s` : "-"} />
      <Metric
        label="Telegram"
        value={status?.telegram_configured ? "configured" : "not configured"}
      />

      <div className="ml-auto flex items-center gap-3">
        <span
          className="flex items-center gap-1.5 text-xs text-muted"
          title={connected ? "Live updates connected" : "Live updates disconnected, polling instead"}
        >
          {connected ? <WifiHigh size={14} /> : <WifiSlash size={14} />}
          {connected ? "live" : "polling"}
        </span>

        <button
          onClick={onScan}
          disabled={scanning}
          className="flex items-center gap-1.5 rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-foreground transition-transform active:scale-[0.98] disabled:opacity-60"
        >
          {scanning ? (
            <CircleNotch size={14} className="animate-spin" />
          ) : (
            <ArrowsClockwise size={14} weight="bold" />
          )}
          Scan now
        </button>
      </div>

      {status?.scanner_error && (
        <div className="flex w-full items-center gap-1.5 text-xs text-bearish">
          <WarningCircle size={12} />
          Last scan error: {status.scanner_error}
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-sm">
      <span className="text-muted">{label}: </span>
      <span className="font-mono text-foreground">{value}</span>
    </div>
  );
}
