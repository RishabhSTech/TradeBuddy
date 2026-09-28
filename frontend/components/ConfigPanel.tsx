"use client";

import { useState } from "react";
import { CheckCircle, FloppyDisk } from "@phosphor-icons/react";
import type { Config, ConfigUpdate } from "@/lib/types";

const ALL_INTERVALS = ["5m", "15m", "1h", "1d"];

const INDICATOR_FIELDS: { key: string; label: string; step?: number }[] = [
  { key: "rsi_period", label: "RSI period" },
  { key: "macd_fast", label: "MACD fast" },
  { key: "macd_slow", label: "MACD slow" },
  { key: "macd_signal", label: "MACD signal" },
  { key: "ema_fast", label: "EMA fast" },
  { key: "ema_slow", label: "EMA slow" },
  { key: "ema_trend", label: "EMA trend" },
  { key: "atr_period", label: "ATR period" },
  { key: "rel_volume_window", label: "Rel. volume window" },
];

const VOLUME_PROFILE_FIELDS: { key: string; label: string; step?: number }[] = [
  { key: "bins", label: "Bins" },
  { key: "value_area_pct", label: "Value area %", step: 0.01 },
  { key: "lookback_bars", label: "Lookback bars" },
];

const LEVEL_FIELDS: { key: string; label: string; step?: number }[] = [
  { key: "atr_stop_mult", label: "ATR stop multiple", step: 0.1 },
  { key: "measured_move_mult", label: "Measured-move multiple", step: 0.1 },
];

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
  const [indicatorParams, setIndicatorParams] = useState<Record<string, number>>(
    config.indicator_params
  );
  const [volumeProfileParams, setVolumeProfileParams] = useState<Record<string, number>>(
    config.volume_profile_params
  );
  const [levelParams, setLevelParams] = useState<Record<string, number>>(config.level_params);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  function setField(
    set: React.Dispatch<React.SetStateAction<Record<string, number>>>,
    key: string,
    value: number
  ) {
    set((prev) => ({ ...prev, [key]: value }));
  }

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
        indicator_params: indicatorParams,
        volume_profile_params: volumeProfileParams,
        level_params: levelParams,
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

      <div>
        <h3 className="mb-2 text-sm font-medium text-foreground">Indicators &amp; levels</h3>
        <p className="mb-3 text-xs text-muted">
          Shared across every detector: the technical-indicator pass, the volume profile a
          stretch target is drawn from, and how each signal&apos;s entry/stop/target plan is
          sized.
        </p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {INDICATOR_FIELDS.map((f) => (
            <NumberField
              key={f.key}
              label={f.label}
              value={indicatorParams[f.key]}
              step={f.step}
              onChange={(v) => setField(setIndicatorParams, f.key, v)}
            />
          ))}
          {VOLUME_PROFILE_FIELDS.map((f) => (
            <NumberField
              key={f.key}
              label={f.label}
              value={volumeProfileParams[f.key]}
              step={f.step}
              onChange={(v) => setField(setVolumeProfileParams, f.key, v)}
            />
          ))}
          {LEVEL_FIELDS.map((f) => (
            <NumberField
              key={f.key}
              label={f.label}
              value={levelParams[f.key]}
              step={f.step}
              onChange={(v) => setField(setLevelParams, f.key, v)}
            />
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

function NumberField({
  label,
  value,
  step,
  onChange,
}: {
  label: string;
  value: number | undefined;
  step?: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-sm">
      <span className="text-muted">{label}</span>
      <input
        type="number"
        step={step ?? 1}
        value={value ?? ""}
        onChange={(e) => onChange(Number(e.target.value))}
        className="rounded-md border border-border bg-background px-2.5 py-1.5 font-mono text-foreground focus:border-accent focus:outline-none"
      />
    </label>
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
