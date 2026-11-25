import { api } from '../api/client'

export interface SchemaColumn {
  name: string
  type: string
  is_numeric: boolean
  is_datetime?: boolean
  sample_values: string[]
  null_count?: number
}

export interface SQLResult {
  columns: string[]
  rows: Record<string, unknown>[]
  row_count: number
  execution_time_ms: number
  truncated: boolean
}

export interface SQLGenerationResponse {
  success: boolean
  sql: string
  explanation: string
  tables_used: string[]
  columns_used: string[]
  query_type: string
  assumptions: string[]
  warnings: string[]
  is_ambiguous: boolean
  clarifying_questions: string[]
}

export interface SQLExplanationResponse {
  success: boolean
  explanation: string
  tables_referenced: string[]
  columns_referenced: string[]
  aggregations_used: string[]
  has_filters: boolean
  has_group_by: boolean
  has_order_by: boolean
  limit: number | null
  performance_notes: string[]
}

export interface SQLValidationResponse {
  success: boolean
  valid: boolean
  error: string | null
  query_plan: string[]
  read_only: boolean
}

export interface SQLSuggestionItem {
  title: string
  prompt: string
  category: string
  sql: string
}

export interface QueryHistoryRecord {
  id: string
  query: string
  name?: string
  timestamp: string
  execution_time_ms?: number
  row_count?: number
  status: 'success' | 'error'
  error_message?: string
  is_favorite?: boolean
}

export const sqlStudioService = {
  async getSchema(datasetId: number): Promise<{ columns: SchemaColumn[]; total_rows: number }> {
    const res = await api.get(`/analytics/${datasetId}/schema`)
    return res.data
  },

  async executeSQL(datasetId: number, query: string, limit: number = 500): Promise<SQLResult> {
    const res = await api.post(`/analytics/${datasetId}/sql`, { query, limit })
    return res.data
  },

  async generateSQL(datasetId: number, prompt: string, autoSuggest: boolean = false): Promise<SQLGenerationResponse> {
    const res = await api.post(`/analytics/${datasetId}/sql/generate`, { prompt, auto_suggest: autoSuggest })
    return res.data
  },

  async explainSQL(datasetId: number, query: string): Promise<SQLExplanationResponse> {
    const res = await api.post(`/analytics/${datasetId}/sql/explain`, { query })
    return res.data
  },

  async validateSQL(datasetId: number, query: string): Promise<SQLValidationResponse> {
    const res = await api.post(`/analytics/${datasetId}/sql/validate`, { query })
    return res.data
  },

  async getSuggestions(datasetId: number): Promise<SQLSuggestionItem[]> {
    const res = await api.get(`/analytics/${datasetId}/sql/suggestions`)
    return res.data.suggestions || []
  },
}
