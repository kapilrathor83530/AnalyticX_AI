export interface ScenarioAdjustment {
  field: string
  mode: 'percent' | 'absolute'
  value: number
}

export interface ScenarioRunPayload {
  dataset_id: number
  name: string
  description?: string
  adjustments: ScenarioAdjustment[]
  metric_columns: Record<string, string>
  elasticity?: number
}

export interface Scenario {
  id: number
  dataset_id: number
  name: string
  description?: string
  baseline_metrics: Record<string, unknown>
  assumptions: Record<string, unknown>
  adjustments: Record<string, unknown>
  results: {
    scenario?: Record<string, number>
    baseline?: Record<string, number>
    differences?: Record<
      string,
      { baseline: number; scenario: number; diff: number; diff_percent: number | null }
    >
  }
  created_at: string
}
