import { api } from '../api/client'
import type {
  ForecastingRecommendation,
  ForecastRun,
  ForecastTrainPayload,
  TimeSeriesReadiness,
} from '../types/forecast'

export const forecastService = {
  async train(payload: ForecastTrainPayload): Promise<ForecastRun> {
    const response = await api.post<ForecastRun>('/forecasting/train', payload)
    return response.data
  },

  async list(datasetId: number): Promise<ForecastRun[]> {
    const response = await api.get<ForecastRun[]>(`/forecasting/${datasetId}`)
    return response.data
  },

  async getRun(runId: number): Promise<ForecastRun> {
    const response = await api.get<ForecastRun>(`/forecasting/run/${runId}`)
    return response.data
  },

  async inspect(datasetId: number): Promise<TimeSeriesReadiness> {
    const response = await api.post<TimeSeriesReadiness>('/forecasting/inspect', {
      dataset_id: datasetId,
    })
    return response.data
  },

  async pinToDashboard(runId: number): Promise<{ success: boolean; dashboard_id: number; route: string }> {
    const response = await api.post(`/forecasting/run/${runId}/pin`)
    return response.data
  },

  async chat(runId: number, question: string): Promise<{ question: string; answer: string; confidence: number }> {
    const response = await api.post(`/forecasting/run/${runId}/chat`, { question })
    return response.data
  },

  async getRecommendation(datasetId: number): Promise<ForecastingRecommendation> {
    const response = await api.get<ForecastingRecommendation>(`/forecasting/recommendation/${datasetId}`)
    return response.data
  },
}
