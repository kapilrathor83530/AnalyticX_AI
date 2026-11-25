export interface AgentStep {
  agent: string
  tool: string
  status: 'ok' | 'error' | 'skipped'
  message: string
  result?: Record<string, unknown>
  duration_ms?: number
}

export interface AgentQueryResponse {
  question: string
  answer: string
  tools_used: string[]
  steps: AgentStep[]
  missing_info: string[]
  verified_facts?: string[]
  limitations?: string[]
  chart_config?: {
    chart_type: string
    title?: string
    data_mapping: Record<string, string | string[]>
    aggregation?: string
    appearance?: Record<string, unknown>
    filters?: Record<string, unknown>[]
  } | null
  available: boolean
  error?: string
}

export interface BusinessChatResponse {
  answer: string
  verified_facts: string[]
  limitations: string[]
  suggested_questions: string[]
  tools_used: string[]
  chart_config?: {
    chart_type: string
    title?: string
    data_mapping: Record<string, string | string[]>
    aggregation?: string
    appearance?: Record<string, unknown>
    filters?: Record<string, unknown>[]
  } | null
  available: boolean
  model: string
}
