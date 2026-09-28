"use client";

import { useState } from "react";
import { CheckCircle, FloppyDisk } from "@phosphor-icons/react";
import type { Config, ConfigUpdate } from "@/lib/types";

const ALL_INTERVALS = ["5m", "15m", "1h", "1d"];

export function ConfigPanel({
  config,
  onSave,
}: {
  config: Config;
  onSave: (patch: ConfigUpdate) => Promise<void>;
}) {
  const [indices, setIndices] = useState<string[]>(config.indices);
  const [intervals, setIntervals] = useState<string[]>(config.intervals);
  const [detectors, setDetectors] = useState<string[]>(config.detectors_enabled);
  const [pollSeconds, setPollSeconds] = useState(config.poll_seconds);
  const [onlyMarketHours, setOnlyMarketHours] = useState(config.only_market_hours);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  function toggle(list: string[], set: (v: string[]) => void, value: string) {
    set(list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);
  }

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    try {
      await onSave({
        indices,
        intervals,
        detectors_enabled: detectors,
        poll_seconds: pollSeconds,
        only_market_hours: onlyMarketHours,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-5 rounded-lg border border-border bg-surface p-4">
      <div>
        <h3 className="mb-2 text-sm font-medium text-foreground">Indices</h3>
        <div className="flex flex-wrap gap-2">
          {config.available_indices.map((idx) => (
            <Pill
              key={idx}
              active={indices.includes(idx)}
              onClick={() => toggle(indices, setIndices, idx)}
            >
              {idx}
            </Pill>
          ))}
        </div>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-medium text-foreground">Intervals</h3>
        <div className="flex flex-wrap gap-2">
          {ALL_INTERVALS.map((iv) => (
            <Pill
              key={iv}
              active={intervals.includes(iv)}
              onClick={() => toggle(intervals, setIntervals, iv)}
            >
              {iv}
            </Pill>
          ))}
        </div>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-medium text-foreground">Detectors</h3>
        <div className="flex flex-wrap gap-2">
          {config.available_detectors.map((det) => (
            <Pill
              key={det}
              active={detectors.includes(det)}
              onClick={() => toggle(detectors, setDetectors, det)}
            >
              {det.replace("_", " ")}
            </Pill>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap items-end gap-6">
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="text-muted">Poll interval (seconds)</span>
          <input
            type="number"
            min={30}
            max={3600}
            value={pollSeconds}
            onChange={(e) => setPollSeconds(Number(e.target.value))}
            className="w-32 rounded-md border border-border bg-background px-2.5 py-1.5 font-mono text-foreground focus:border-accent focus:outline-none"
          />
        </label>

        <label className="flex items-center gap-2 pb-1.5 text-sm text-foreground">
          <input
            type="checkbox"
            checked={onlyMarketHours}
            onChange={(e) => setOnlyMarketHours(e.target.checked)}
            className="h-4 w-4 rounded border-border accent-accent"
          />
          Only scan during market hours
        </label>

        <button
          onClick={handleSave}
          disabled={saving}
          className="ml-auto flex items-center gap-1.5 rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-foreground transition-transform active:scale-[0.98] disabled:opacity-60"
        >
          {saved ? <CheckCircle size={14} weight="bold" /> : <FloppyDisk size={14} weight="bold" />}
          {saved ? "Saved" : saving ? "Saving..." : "Save config"}
        </button>
      </div>
    </div>
  );
}

function Pill({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full border px-3 py-1 text-sm capitalize transition-colors ${
        active
          ? "border-accent bg-accent/15 text-accent"
          : "border-border text-muted hover:text-foreground"
      }`}
    >
      {children}
    </button>
  );
}
