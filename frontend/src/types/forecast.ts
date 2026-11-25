export interface ForecastTrainPayload {
  dataset_id: number
  date_column: string
  target_column: string
  horizon: number
  frequency: string
  model_type?: string
  group_dimension?: string
  group_value?: string
  fill_strategy?: 'interpolate' | 'ffill' | 'zero' | 'mean'
  handle_outliers?: boolean
  custom_assumptions?: {
    growth_rate_pct?: number
    price_change_pct?: number
    price_elasticity?: number
    marketing_budget_pct?: number
    marketing_elasticity?: number
  }
}

export interface ForecastMetrics {
  mae?: number
  rmse?: number
  wape?: number
  mase?: number
  mape?: number
  r2?: number
  baseline_mae?: number
  baseline_rmse?: number
  baseline_wape?: number
  wape_improvement_vs_naive_pct?: number
}

export interface ForecastPoint {
  date: string
  value: number
  lower_80?: number
  upper_80?: number
  lower_95?: number
  upper_95?: number
}

export interface CandidateModelInfo {
  key: string
  name: string
  description: string
  parameters?: Record<string, any>
  metrics: ForecastMetrics
  status: 'evaluated' | 'failed'
}

export interface ForecastScenario {
  name: string
  description: string
  values: number[]
  total: number
  delta_vs_baseline: number
  delta_pct_vs_baseline: number
  assumptions?: Record<string, any>
}

export interface ForecastInsights {
  direction?: string
  percent_change?: number
  trailing_history_mean?: number
  forecast_mean?: number
  net_delta?: number
  peak?: { date: string; value: number }
  trough?: { date: string; value: number }
  executive_summary?: string
  pattern_description?: string
  uncertainty_assessment?: string
  recommendations?: string[]
  limitations?: string[]
}

export interface ForecastRun {
  id: number
  dataset_id: number
  model_type: string
  target_column: string
  date_column: string
  group_dimension?: string
  group_value?: string
  horizon: number
  frequency: string
  metrics: ForecastMetrics
  predictions: ForecastPoint[]
  candidate_models?: CandidateModelInfo[]
  backtest_results?: {
    dates: string[]
    actual: number[]
    models: Record<string, number[]>
  }
  confidence_intervals?: {
    lower_80: number[]
    upper_80: number[]
    lower_95: number[]
    upper_95: number[]
  }
  scenarios?: Record<string, ForecastScenario>
  insights?: ForecastInsights
  data_validation?: Record<string, any>
  training_time_ms?: number
  notes?: string
  created_at: string
}

export interface TimeSeriesReadiness {
  is_ready: boolean
  reason: string
  row_count: number
  date_candidates: {
    column: string
    valid_percent: number
    min_date?: string
    max_date?: string
    unique_dates: number
  }[]
  target_candidates: {
    column: string
    mean: number
    std: number
    is_non_negative: boolean
    missing_count: number
  }[]
  group_candidates: {
    column: string
    unique_count: number
    top_values: string[]
  }[]
  recommended_date_column?: string
  recommended_target_column?: string
  recommended_frequency?: string
}

export interface ForecastingRecommendation {
  has_recommendation: boolean
  title?: string
  message?: string
  date_column?: string
  target_column?: string
  frequency?: string
  route?: string
  readiness?: TimeSeriesReadiness
  error?: string
}
