export interface GoldPrice {
  id: number;
  timestamp: string;
  xau_usd: number;
  au9999: number;
  usd_cny: number;
  premium: number;
}

export interface MacroIndicator {
  id: number;
  date: string;
  tips_10y: number | null;
  dxy: number | null;
  spdr_tonnes: number | null;
  cot_net_long: number | null;
  vix: number | null;
}

export interface ScoreResult {
  calc_time: string;
  total_score: number;
  signal: string;
  confidence: number;
  indicator_scores: Record<string, number>;
  weights_used: Record<string, number>;
}

export interface CBEvent {
  id: number;
  event_date: string;
  country: string;
  action: string;
  amount_tonnes: number | null;
  impact_score: number;
  source_url: string;
}

export interface DashboardData {
  updated_at: string;
  prices: GoldPrice | null;
  macro: MacroIndicator | null;
  score: ScoreResult | null;
  cb_events: CBEvent[];
}

export interface AccuracyStats {
  records: PredictionRecord[];
  total_count: number;
  correct_count: number;
  total_accuracy: number;
  rolling_30d_count: number;
  rolling_30d_correct: number;
  rolling_30d_accuracy: number;
}

export interface PredictionRecord {
  id: number;
  pred_date: string;
  target_date: string;
  predicted_direction: string;
  predicted_change_pct: number;
  rule_score: number;
  llm_consensus: string;
  actual_px_change: number | null;
  is_correct: number | null;
  error_reason: string | null;
}

export interface SSEEvent {
  type: 'status' | 'partial' | 'result';
  phase?: string;
  message?: string;
  model?: string;
  content?: string;
  consensus?: string;
  direction?: string;
  confidence?: number;
  score?: number;
}
