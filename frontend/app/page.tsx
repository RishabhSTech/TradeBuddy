"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Binoculars, ListMagnifyingGlass, SlidersHorizontal } from "@phosphor-icons/react";
import { api, ApiError } from "@/lib/api";
import type { Config, ConfigUpdate, Signal, Status } from "@/lib/types";
import { StatusBar } from "@/components/StatusBar";
import { SignalCard } from "@/components/SignalCard";
import { ConfigPanel } from "@/components/ConfigPanel";
import { ReplayPanel } from "@/components/ReplayPanel";

type Tab = "signals" | "config" | "replay";

export default function Home() {
  const [status, setStatus] = useState<Status | null>(null);
  const [config, setConfig] = useState<Config | null>(null);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [newIds, setNewIds] = useState<Set<number>>(new Set());
  const [connected, setConnected] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [tab, setTab] = useState<Tab>("signals");
  const [indexFilter, setIndexFilter] = useState<string>("ALL");
  const [loadError, setLoadError] = useState<string | null>(null);

  const signalsRef = useRef<Signal[]>([]);
  useEffect(() => {
    signalsRef.current = signals;
  }, [signals]);

  const loadInitial = useCallback(async () => {
    try {
      const [statusRes, configRes, signalsRes] = await Promise.all([
        api.status(),
        api.config(),
        api.signals({ limit: 100 }),
      ]);
      setStatus(statusRes);
      setConfig(configRes);
      setSignals(signalsRes);
      setLoadError(null);
    } catch (err) {
      setLoadError(
        err instanceof ApiError
          ? err.message
          : `Could not reach the TradeBuddy API at ${api.base}. Is the backend running?`
      );
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial data load on mount
    loadInitial();
    const statusInterval = window.setInterval(() => {
      api.status().then(setStatus).catch(() => {});
    }, 15000);
    return () => window.clearInterval(statusInterval);
  }, [loadInitial]);

  useEffect(() => {
    const source = new EventSource(api.streamUrl());
    source.addEventListener("connected", () => setConnected(true));
    source.addEventListener("signal", (event) => {
      const data: Signal = JSON.parse((event as MessageEvent).data);
      if (signalsRef.current.some((s) => s.id === data.id)) return;
      setSignals((prev) => [data, ...prev].slice(0, 200));
      setNewIds((prev) => new Set(prev).add(data.id));
      window.setTimeout(() => {
        setNewIds((prev) => {
          const next = new Set(prev);
          next.delete(data.id);
          return next;
        });
      }, 6000);
    });
    source.onerror = () => setConnected(false);
    return () => source.close();
  }, []);

  async function handleScan() {
    setScanning(true);
    try {
      await api.triggerScan();
      const [statusRes, signalsRes] = await Promise.all([api.status(), api.signals({ limit: 100 })]);
      setStatus(statusRes);
      setSignals(signalsRes);
    } catch {
      // status bar shows scanner_error from the next poll if this failed server-side
    } finally {
      setScanning(false);
    }
  }

  async function handleConfigSave(patch: ConfigUpdate) {
    const updated = await api.updateConfig(patch);
    setConfig(updated);
    const statusRes = await api.status();
    setStatus(statusRes);
  }

  const filteredSignals =
    indexFilter === "ALL" ? signals : signals.filter((s) => s.index_key === indexFilter);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-4 px-4 py-6 sm:px-6">
      <header className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <Binoculars size={22} weight="bold" className="text-accent" />
          <h1 className="text-lg font-semibold text-foreground">TradeBuddy</h1>
        </div>
        <p className="text-sm text-muted">
          Alert-only pattern watcher for Nifty 50, Bank Nifty and Sensex. It never places an
          order, it only tells you when a chart pattern breaks out.
        </p>
      </header>

      {loadError ? (
        <div className="rounded-lg border border-bearish/40 bg-bearish/10 px-4 py-3 text-sm text-bearish">
          {loadError}
        </div>
      ) : (
        <StatusBar status={status} connected={connected} scanning={scanning} onScan={handleScan} />
      )}

      <nav className="flex gap-1 border-b border-border">
        <TabButton active={tab === "signals"} onClick={() => setTab("signals")} icon={<ListMagnifyingGlass size={15} />}>
          Signals
        </TabButton>
        <TabButton active={tab === "config"} onClick={() => setTab("config")} icon={<SlidersHorizontal size={15} />}>
          Config
        </TabButton>
        <TabButton active={tab === "replay"} onClick={() => setTab("replay")} icon={<Binoculars size={15} />}>
          Replay
        </TabButton>
      </nav>

      {tab === "signals" && (
        <div className="flex flex-col gap-3">
          {config && (
            <div className="flex flex-wrap gap-2">
              <FilterPill active={indexFilter === "ALL"} onClick={() => setIndexFilter("ALL")}>
                All
              </FilterPill>
              {config.available_indices.map((idx) => (
                <FilterPill key={idx} active={indexFilter === idx} onClick={() => setIndexFilter(idx)}>
                  {idx}
                </FilterPill>
              ))}
            </div>
          )}

          {filteredSignals.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border px-4 py-10 text-center text-sm text-muted">
              No signals yet. TradeBuddy scans automatically during market hours, or hit
              &ldquo;Scan now&rdquo; above to check right now.
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {filteredSignals.map((signal) => (
                <SignalCard key={signal.id} signal={signal} isNew={newIds.has(signal.id)} />
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "config" && config && <ConfigPanel config={config} onSave={handleConfigSave} />}

      {tab === "replay" && config && <ReplayPanel config={config} />}

      <footer className="mt-auto border-t border-border pt-4 text-xs text-muted">
        Decision-support only, not investment advice. TradeBuddy never places, modifies or
        cancels an order.
      </footer>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm transition-colors ${
        active
          ? "border-accent text-foreground"
          : "border-transparent text-muted hover:text-foreground"
      }`}
    >
      {icon}
      {children}
    </button>
  );
}

function FilterPill({
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
      className={`rounded-full border px-3 py-1 text-xs transition-colors ${
        active ? "border-accent bg-accent/15 text-accent" : "border-border text-muted hover:text-foreground"
      }`}
    >
      {children}
    </button>
  );
}
