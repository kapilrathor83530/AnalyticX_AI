import { api } from '../api/client'
import type { ChartRecommendation, ChartRenderResponse, ChartTypeDefinition, ChartValidationResult } from '../types/chart'
import type { Dashboard, Widget, WidgetCreatePayload, WidgetUpdatePayload } from '../types/dashboard'

export const dashboardService = {
  async list(datasetId?: number, search?: string): Promise<Dashboard[]> {
    const params = { ...(datasetId ? { dataset_id: datasetId } : {}), ...(search ? { search } : {}) }
    const response = await api.get<Dashboard[]>('/dashboards', { params })
    return response.data
  },

  async create(payload: { dataset_id: number; name: string; description?: string }): Promise<Dashboard> {
    const response = await api.post<Dashboard>('/dashboards', payload)
    return response.data
  },

  async get(dashboardId: number): Promise<Dashboard> {
    const response = await api.get<Dashboard>(`/dashboards/${dashboardId}`)
    return response.data
  },

  async update(dashboardId: number, payload: Partial<Dashboard>): Promise<Dashboard> {
    const response = await api.put<Dashboard>(`/dashboards/${dashboardId}`, payload)
    return response.data
  },

  async remove(dashboardId: number): Promise<void> {
    await api.delete(`/dashboards/${dashboardId}`)
  },

  async duplicate(dashboardId: number, name?: string): Promise<Dashboard> {
    const response = await api.post<Dashboard>(`/dashboards/${dashboardId}/duplicate`, name ? { name } : {})
    return response.data
  },

  async exportConfig(dashboardId: number): Promise<Record<string, unknown>> {
    const response = await api.get<Record<string, unknown>>(`/dashboards/${dashboardId}/export`)
    return response.data
  },

  async restore(config: Record<string, unknown>, name?: string): Promise<Dashboard> {
    const response = await api.post<Dashboard>('/dashboards/restore', { configuration: config, name })
    return response.data
  },

  async saveLayout(dashboardId: number, layoutConfig: Record<string, unknown>): Promise<Dashboard> {
    const response = await api.put<Dashboard>(`/dashboards/${dashboardId}/layout`, { layout_config: layoutConfig })
    return response.data
  },

  async listWidgets(dashboardId: number): Promise<Widget[]> {
    const response = await api.get<Widget[]>(`/dashboards/${dashboardId}/widgets`)
    return response.data
  },

  async addWidget(dashboardId: number, payload: WidgetCreatePayload): Promise<Widget> {
    const response = await api.post<Widget>(`/dashboards/${dashboardId}/widgets`, payload)
    return response.data
  },

  async updateWidget(dashboardId: number, widgetId: number, payload: WidgetUpdatePayload): Promise<Widget> {
    const response = await api.put<Widget>(`/dashboards/${dashboardId}/widgets/${widgetId}`, payload)
    return response.data
  },

  async removeWidget(dashboardId: number, widgetId: number): Promise<void> {
    await api.delete(`/dashboards/${dashboardId}/widgets/${widgetId}`)
  },

  async listCharts(): Promise<ChartTypeDefinition[]> {
    const response = await api.get<ChartTypeDefinition[]>('/visualizations/charts')
    return response.data
  },

  async recommendCharts(datasetId: number, query = '', limit = 8): Promise<{ dataset_id: number; dataset_version: number; recommendations: ChartRecommendation[] }> {
    const response = await api.get<{ dataset_id: number; dataset_version: number; recommendations: ChartRecommendation[] }>(
      `/visualizations/recommend/${datasetId}`,
      { params: { query, limit } }
    )
    return response.data
  },

  async validateChart(datasetId: number, config: Record<string, unknown>): Promise<ChartValidationResult> {
    const response = await api.post<ChartValidationResult>('/visualizations/validate', {
      dataset_id: datasetId,
      config,
    })
    return response.data
  },

  async renderChart(datasetId: number, config: Record<string, unknown>, signal?: AbortSignal): Promise<ChartRenderResponse> {
    const response = await api.post<ChartRenderResponse>('/visualizations/render', {
      dataset_id: datasetId,
      config,
    }, { timeout: 120_000, signal })
    return response.data
  },
}
