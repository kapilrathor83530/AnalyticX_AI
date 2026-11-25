export interface Dataset {
  id: number
  name: string
  original_filename: string
  size_bytes: number
  row_count: number
  column_count: number
  status?: string
  parent_id?: number | null
  version?: number
  quality_score?: number | null
  dataset_metadata?: Record<string, unknown> | null
  created_at: string
}

export interface DatasetPreview {
  columns: string[]
  rows: Record<string, unknown>[]
  total_rows: number
  returned_rows: number
}

export interface ColumnProfile {
  name: string
  dtype: string
  inferred_type: string
  missing_count: number
  missing_percent: number
  unique_count: number
  sample_values: unknown[]
}

export interface DatasetProfile {
  row_count: number
  column_count: number
  duplicate_rows: number
  columns: ColumnProfile[]
  numeric_summary: Record<string, Record<string, unknown>>
  categorical_summary: Record<string, { value: unknown; count: number }[]>
}

export interface EDA extends DatasetProfile {
  correlations: Record<string, Record<string, number | null>>
  numeric_distributions: Record<string, { bins: number[]; counts: number[] }>
}

export interface CleaningAlternative {
  strategy: string
  label: string
  description: string
}

export interface CleaningRecommendation {
  id: string
  issue_type: string
  column: string | null
  title: string
  severity: 'high' | 'medium' | 'low'
  affected_count: number
  affected_percent: number
  example_values: unknown[]
  why_it_matters: string
  recommended_action: string
  available_alternatives: CleaningAlternative[]
  expected_effect: string
  safe_for_auto: boolean
  config: Record<string, unknown>
}

export interface QualityReport {
  dataset_shape: { rows: number; columns: number }
  quality_score: number
  score_breakdown: {
    initial_score: number
    missing_penalty: number
    duplicate_penalty: number
    outlier_penalty: number
    constant_penalty: number
  }
  summary: {
    total_missing_cells: number
    missing_cells_pct: number
    columns_with_missing: number
    duplicate_rows: number
    duplicate_pct: number
    columns_with_outliers: number
    constant_columns: string[]
    id_candidate_columns: string[]
  }
  missing_by_column: Record<string, {
    count: number
    percent: number
    severity: string
    dtype: string
    inferred_type: string
  }>
  outliers_by_column: Record<string, {
    outlier_count: number
    percent: number
    lower_bound: number
    upper_bound: number
    q1: number
    q3: number
    iqr: number
    sample_values: unknown[]
    severity: string
  }>
  formatting_issues: Record<string, {
    whitespace_count: number
    mixed_casing: boolean
    sample_values: unknown[]
  }>
  recommendations: CleaningRecommendation[]
}

export interface InsightItem {
  id: string
  statement: string
  evidence: string
  type: string
}

export interface EdaReport {
  dataset_name: string
  row_count: number
  column_count: number
  data_dictionary: Array<{
    name: string
    dtype: string
    inferred_type: string
    unique_count: number
    missing_count: number
    missing_percent: number
    sample_values: unknown[]
    role_hint: string
  }>
  numeric_statistics: Record<string, {
    count: number
    mean: number
    std: number
    min: number
    p25: number
    median: number
    p75: number
    max: number
    skew: number
  }>
  numeric_distributions: Record<string, { bins: number[]; counts: number[] }>
  categorical_breakdowns: Record<string, Array<{ category: string; count: number; percentage: number }>>
  correlation_matrix: Record<string, Record<string, number | null>>
  notable_correlations: Array<{
    col1: string
    col2: string
    correlation: number
    strength: string
    direction: string
  }>
  time_trends?: {
    date_column?: string
    target_column?: string
    dates?: string[]
    values?: number[]
  }
  insights_report: {
    dataset_summary: InsightItem[]
    column_findings: InsightItem[]
    relationships: InsightItem[]
    anomalies: InsightItem[]
    business_insights: InsightItem[]
    recommended_next_steps: InsightItem[]
  }
}

export interface TransformationRecord {
  id: number
  dataset_id: number
  transformation_type: string
  description?: string
  parameters: Record<string, unknown>
  columns_affected?: string[]
  status: string
  trigger_source: string
  row_count_before: number
  row_count_after: number
  applied_at: string
}
