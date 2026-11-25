export interface Widget {
  id: number
  dashboard_id: number
  chart_type: string
  title: string
  config: Record<string, unknown>
  data_mapping: Record<string, unknown>
  position: { x: number; y: number }
  size: { w: number; h: number }
  created_at: string
  updated_at?: string
}

export interface Dashboard {
  id: number
  dataset_id: number
  workspace_id?: number | null
  name: string
  description?: string
  layout_config: Record<string, unknown>
  is_default: boolean
  created_at: string
  updated_at?: string
}

export interface WidgetCreatePayload {
  chart_type: string
  title: string
  config?: Record<string, unknown>
  data_mapping?: Record<string, unknown>
  position?: { x: number; y: number }
  size?: { w: number; h: number }
}

export interface WidgetUpdatePayload {
  chart_type?: string
  title?: string
  config?: Record<string, unknown>
  data_mapping?: Record<string, unknown>
  position?: { x: number; y: number }
  size?: { w: number; h: number }
}
