import { api } from '../api/client'
import type { EdaReport, QualityReport, TransformationRecord } from '../types'

export interface CleaningActionRequest {
  action_type: string
  column?: string | null
  strategy?: string
  parameters?: Record<string, unknown>
  save_as_new_version?: boolean
}

export interface CleaningActionResult {
  success: boolean
  dataset_id: number
  action: {
    action_type: string
    column?: string
    strategy?: string
    description: string
    rows_before: number
    rows_after: number
    affected_records: number
  }
  before: { rows: number; columns: number; quality_score: number }
  after: { rows: number; columns: number; quality_score: number }
  quality_report: QualityReport
}

export interface AutoCleanResult {
  success: boolean
  dataset_id: number
  operations_count: number
  applied_actions: Array<{ description: string; action_type: string; column?: string }>
  before: { rows: number; quality_score: number }
  after: { rows: number; quality_score: number }
  quality_report: QualityReport
}

export interface AnalystChatResponse {
  answer: string
  executed_action?: {
    type: string
    details: string | Record<string, unknown>
    result?: unknown
  } | null
  verified_facts?: string[]
  suggested_questions?: string[]
}

export const dataPrepService = {
  async getQualityReport(datasetId: number): Promise<QualityReport> {
    const res = await api.get<QualityReport>(`/datasets/${datasetId}/quality-report`)
    return res.data
  },

  async applyAction(datasetId: number, payload: CleaningActionRequest): Promise<CleaningActionResult> {
    const res = await api.post<CleaningActionResult>(`/datasets/${datasetId}/apply-action`, payload)
    return res.data
  },

  async autoClean(datasetId: number, saveAsNewVersion: boolean = false): Promise<AutoCleanResult> {
    const res = await api.post<AutoCleanResult>(`/datasets/${datasetId}/auto-clean`, {
      save_as_new_version: saveAsNewVersion,
    })
    return res.data
  },

  async undo(datasetId: number): Promise<{ success: boolean; reverted_transformation?: string }> {
    const res = await api.post(`/datasets/${datasetId}/undo`)
    return res.data
  },

  async getEdaReport(datasetId: number): Promise<EdaReport> {
    const res = await api.get<EdaReport>(`/datasets/${datasetId}/eda-report`)
    return res.data
  },

  async getTransformations(datasetId: number): Promise<TransformationRecord[]> {
    const res = await api.get<TransformationRecord[]>(`/datasets/${datasetId}/transformations`)
    return res.data
  },

  getExportUrl(datasetId: number, format: 'csv' | 'xlsx' | 'log' | 'report'): string {
    return `/api/v1/datasets/${datasetId}/export/${format}`
  },

  async sendAnalystChat(
    datasetId: number,
    messages: Array<{ role: string; content: string }>,
    selectedColumn?: string | null
  ): Promise<AnalystChatResponse> {
    const res = await api.post<AnalystChatResponse>(`/datasets/${datasetId}/analyst-chat`, {
      messages,
      selected_column: selectedColumn || undefined,
    })
    return res.data
  },
}
