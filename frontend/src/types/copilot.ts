export interface WorkspaceContext {
  workspace_mode?: string
  dataset_id?: number
  dataset_name?: string
  document_id?: string
  page_number?: number
  selected_column?: string | null
  dashboard_id?: number
  dashboard_name?: string
  widget_id?: number
  widget_title?: string
  chart_type?: string
  active_filters?: Record<string, unknown>
  language_override?: string
}

export interface Citation {
  page: number
  source_type: string
  snippet: string
  confidence: number
}

export interface CopilotMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  detected_language?: string
  citations?: Citation[]
  verified_facts?: string[]
  business_insights?: string[]
  suggested_questions?: string[]
  executed_action?: {
    type: string
    result: Record<string, unknown>
  } | null
  method_explanation?: string
  isStreaming?: boolean
}

export interface CopilotChatResponse {
  answer: string
  detected_language: string
  language_name: string
  script: string
  active_context?: Record<string, unknown>
  citations: Citation[]
  verified_facts: string[]
  method_explanation?: string
  business_insights: string[]
  suggested_questions: string[]
  executed_action?: {
    type: string
    result: Record<string, unknown>
  } | null
  tools_used: string[]
  available: boolean
  model: string
}

export interface LanguageOption {
  code: string
  name: string
  script: string
  native?: string
  native_name?: string
}
