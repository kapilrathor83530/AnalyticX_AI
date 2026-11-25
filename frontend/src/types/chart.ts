export type ChartCategory = 'comparison' | 'trend' | 'composition' | 'statistical' | 'business'

export interface DataRole {
  name: string
  label: string
  type: 'dimension' | 'measure' | 'date' | 'size' | 'color'
  required: boolean
  multiple: boolean
}

export interface ChartTypeDefinition {
  id: string
  name: string
  category: ChartCategory
  icon: string
  data_roles: DataRole[]
  config_options: string[]
  default_config: Record<string, unknown>
}

export interface ChartConfig {
  chart_type: string
  title?: string
  subtitle?: string
  data_mapping: Record<string, string | string[]>
  filters: { column: string; op: string; value: unknown }[]
  sort?: { column: string; ascending: boolean }
  limit?: number
  appearance: Record<string, unknown>
  aggregation?: string
}

export interface ChartValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
  suggested_alternative?: string | null
}

export interface ChartRecommendation {
  chart_type: string
  title: string
  reason: string
  purpose: string
  priority: number
  data_mapping: Record<string, string | string[]>
  aggregation?: string
  limit?: number | null
  source_columns?: string[]
  preview_row_count?: number
}

export interface ChartRenderResponse {
  chart_type: string
  data: Record<string, unknown>[]
  layout: Record<string, unknown>
  warnings?: string[]
  error?: string
  suggested_alternative?: string | null
  metadata?: {
    dataset_version?: number
    total_source_rows?: number
    rendered_points?: number
    sampled?: boolean
    validation_passed?: boolean
  }
}
