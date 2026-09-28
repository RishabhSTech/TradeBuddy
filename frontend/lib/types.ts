export type Direction = "bullish" | "bearish";

export interface Signal {
  id: number;
  timestamp: string;
  index_key: string;
  interval: string;
  pattern: string;
  direction: Direction;
  breakout_price: number;
  level: number;
  confidence: number;
  note: string;
  chart_data_uri: string | null;
}

export interface Status {
  market_open: boolean;
  now_ist: string;
  last_scan_at: string | null;
  last_scan_found: number | null;
  next_scan_at: string | null;
  poll_seconds: number;
  only_market_hours: boolean;
  indices: string[];
  intervals: string[];
  telegram_configured: boolean;
  scanner_error: string | null;
}

export interface Config {
  indices: string[];
  intervals: string[];
  poll_seconds: number;
  only_market_hours: boolean;
  detectors_enabled: string[];
  detectors_params: Record<string, Record<string, number>>;
  available_indices: string[];
  available_detectors: string[];
}

export interface ConfigUpdate {
  indices?: string[];
  intervals?: string[];
  poll_seconds?: number;
  only_market_hours?: boolean;
  detectors_enabled?: string[];
}

export interface ScanResult {
  new_signals: number;
  signals: Signal[];
}

export interface ReplaySummary {
  index_key: string;
  interval: string;
  horizon_bars: number;
  summary: {
    count: number;
    patterns?: Record<
      string,
      { signals: number; hit_rate_pct: number; avg_forward_return_pct: number }
    >;
  };
}
