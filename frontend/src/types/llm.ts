export interface ModelStatus {
  available: boolean
  active_model: string
  active_model_installed: boolean
  installed_models: { name: string }[]
  error?: string
}

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

export interface ChatResponse {
  answer: string
  model: string
  available: boolean
  error?: string
}

export interface CommandResponse {
  action: string
  chart_type?: string | null
  data_mapping: Record<string, unknown>
  value?: unknown
  clarification_needed: boolean
  clarification_question?: string | null
  available: boolean
  error?: string
}
