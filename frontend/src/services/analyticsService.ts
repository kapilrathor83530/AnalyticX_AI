import { api } from '../api/client'

export const analyticsService = {
  async kpi(datasetId: number, payload: Record<string, unknown>) {
    const response = await api.post(`/analytics/${datasetId}/kpi`, payload)
    return response.data
  },

  async trend(datasetId: number, payload: Record<string, unknown>) {
    const response = await api.post(`/analytics/${datasetId}/trend`, payload)
    return response.data
  },

  async descriptive(datasetId: number, column: string) {
    const response = await api.post(`/analytics/${datasetId}/descriptive`, { column })
    return response.data
  },

  async compareGroups(datasetId: number, groupColumn: string, valueColumn: string) {
    const response = await api.post(`/analytics/${datasetId}/compare-groups`, {
      group_column: groupColumn,
      value_column: valueColumn,
    })
    return response.data
  },

  async anomalies(datasetId: number, column: string, threshold = 3) {
    const response = await api.post(`/analytics/${datasetId}/anomalies`, { column, threshold })
    return response.data
  },
}
