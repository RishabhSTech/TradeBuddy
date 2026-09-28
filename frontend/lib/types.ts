export type Direction = "bullish" | "bearish";
export type TrendDirection = "up" | "down" | "flat";

export interface IndicatorSnapshot {
  rsi14: number | null;
  macd: number | null;
  macd_signal: number | null;
  macd_hist: number | null;
  ema_fast: number | null;
  ema_slow: number | null;
  ema_trend: number | null;
  atr14: number | null;
  vwap: number | null;
  rel_volume: number | null;
  obv: number | null;
  trend_direction: TrendDirection | null;
  trend_strength: number | null;
}

export interface TradePlan {
  entry: number;
  stop: number;
  target1: number;
  target2: number | null;
  risk_per_unit: number;
  reward_to_target1: number;
  r_multiple_1: number;
  r_multiple_2: number | null;
  method: string;
  basis: string[];
}

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
  pattern_height: number | null;
  confidence_breakdown: Record<string, number> | null;
  indicators: IndicatorSnapshot | null;
  volume_levels: { poc: number; vah: number; val: number } | null;
  plan: TradePlan | null;
  analyst_note: string | null;
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
  indicator_params: Record<string, number>;
  level_params: Record<string, number>;
  volume_profile_params: Record<string, number>;
  available_indices: string[];
  available_detectors: string[];
}

export interface ConfigUpdate {
  indices?: string[];
  intervals?: string[];
  poll_seconds?: number;
  only_market_hours?: boolean;
  detectors_enabled?: string[];
  indicator_params?: Record<string, number>;
  level_params?: Record<string, number>;
  volume_profile_params?: Record<string, number>;
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
