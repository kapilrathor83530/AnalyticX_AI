import { api } from '../api/client'
import type {
  ChartExportDataPayload,
  ExportPackagePayload,
  GenerateReportPayload,
  ReportItem,
  ReportListResponse,
} from '../types/report'

export function triggerBrowserDownload(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}

export const reportService = {
  async listReports(params?: {
    dataset_id?: number
    report_type?: string
    export_format?: string
    search?: string
    limit?: number
    offset?: number
  }): Promise<ReportListResponse> {
    const res = await api.get<ReportListResponse>('/reports', { params })
    return res.data
  },

  async getReport(id: number): Promise<ReportItem> {
    const res = await api.get<ReportItem>(`/reports/item/${id}`)
    return res.data
  },

  async generateReport(payload: GenerateReportPayload): Promise<{
    success: boolean
    report_id: number
    title: string
    report_type: string
    export_format: string
    file_size_bytes: number
    download_url: string
  }> {
    const res = await api.post('/reports/generate', payload)
    return res.data
  },

  async downloadSavedReport(reportId: number, filename?: string, format?: string): Promise<void> {
    const res = await api.get(`/reports/${reportId}/download`, {
      params: format ? { format } : undefined,
      responseType: 'blob',
    })
    const disposition = res.headers['content-disposition']
    let finalName = filename
    if (!finalName && disposition) {
      const match = disposition.match(/filename="?([^";]+)"?/)
      if (match && match[1]) finalName = match[1]
    }
    triggerBrowserDownload(res.data, finalName || `report_${reportId}.${format || 'pdf'}`)
  },

  async exportPackage(payload: ExportPackagePayload): Promise<void> {
    const res = await api.post('/reports/export-package', payload, {
      responseType: 'blob',
    })
    triggerBrowserDownload(res.data, `Analyticx_Package_dataset_${payload.dataset_id}.zip`)
  },

  async exportChartData(payload: ChartExportDataPayload): Promise<void> {
    const res = await api.post('/reports/chart/export-data', payload, {
      responseType: 'blob',
    })
    const ext = payload.format === 'xlsx' ? 'xlsx' : 'csv'
    const cleanTitle = payload.title.replace(/[^a-zA-Z0-9_-]/g, '_') || 'chart_data'
    triggerBrowserDownload(res.data, `${cleanTitle}.${ext}`)
  },

  async downloadDirect(endpoint: string, filename: string): Promise<void> {
    const res = await api.get(endpoint, { responseType: 'blob' })
    triggerBrowserDownload(res.data, filename)
  },

  async deleteReport(id: number): Promise<void> {
    await api.delete(`/reports/${id}`)
  },

  async batchDownloadReports(reportIds: number[]): Promise<void> {
    const res = await api.post('/reports/batch-download', { report_ids: reportIds }, { responseType: 'blob' })
    triggerBrowserDownload(res.data, `Analyticx_Selected_Reports_${reportIds.length}_items.zip`)
  },

  async batchDeleteReports(reportIds: number[]): Promise<{ deleted_count: number }> {
    const res = await api.post<{ success: boolean; deleted_count: number }>('/reports/batch-delete', { report_ids: reportIds })
    return res.data
  },

  async exportSingleInsight(insight: any, format: 'pdf' | 'csv' | 'json' | 'docx' = 'pdf'): Promise<void> {
    const res = await api.post('/reports/insight/export', { insight, format }, { responseType: 'blob' })
    const cleanTitle = (insight.title || 'Insight').replace(/[^a-zA-Z0-9_-]/g, '_')
    triggerBrowserDownload(res.data, `Analyticx_Insight_${cleanTitle}.${format}`)
  },
}
