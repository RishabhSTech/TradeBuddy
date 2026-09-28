import type { Config, ConfigUpdate, ReplaySummary, ScanResult, Signal, Status } from "./types";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(
  /\/$/,
  ""
);

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  base: API_BASE,
  status: () => request<Status>("/api/status"),
  signals: (params: { limit?: number; index?: string; pattern?: string } = {}) => {
    const qs = new URLSearchParams();
    if (params.limit) qs.set("limit", String(params.limit));
    if (params.index) qs.set("index", params.index);
    if (params.pattern) qs.set("pattern", params.pattern);
    const suffix = qs.toString() ? `?${qs}` : "";
    return request<Signal[]>(`/api/signals${suffix}`);
  },
  config: () => request<Config>("/api/config"),
  updateConfig: (patch: ConfigUpdate) =>
    request<Config>("/api/config", { method: "PUT", body: JSON.stringify(patch) }),
  triggerScan: () => request<ScanResult>("/api/scan", { method: "POST" }),
  replay: (params: { index: string; interval: string; lookback: string; horizon: number }) => {
    const qs = new URLSearchParams({
      index: params.index,
      interval: params.interval,
      lookback: params.lookback,
      horizon: String(params.horizon),
    });
    return request<ReplaySummary>(`/api/replay?${qs}`);
  },
  streamUrl: () => `${API_BASE}/api/stream`,
};

export { ApiError };
