export type ReportType =
  | 'statistical'
  | 'insights'
  | 'forecast'
  | 'dashboard'
  | 'cleaning'
  | 'simulation'
  | 'package'

export type ExportFormat =
  | 'pdf'
  | 'xlsx'
  | 'csv'
  | 'zip'
  | 'json'
  | 'pptx'
  | 'docx'

export interface ReportItem {
  id: number
  title: string
  report_type: ReportType
  export_format: ExportFormat
  dataset_id: number
  dataset_name: string
  dashboard_id?: number
  file_size_bytes: number
  status: string
  dataset_version: number
  is_stale: boolean
  parameters: Record<string, any>
  report_metadata: Record<string, any>
  created_at: string
  download_url: string
}

export interface ReportListResponse {
  reports: ReportItem[]
  total: number
}

export interface GenerateReportPayload {
  dataset_id: number
  report_type: ReportType
  export_format: ExportFormat
  title?: string
  parameters?: Record<string, any>
}

export interface ExportPackagePayload {
  dataset_id: number
  selected_categories?: string[]
}

export interface ChartExportDataPayload {
  title: string
  columns: string[]
  rows: Record<string, any>[]
  format?: 'csv' | 'xlsx'
}
