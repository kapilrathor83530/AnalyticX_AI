import { api } from '../api/client'
import type { Scenario, ScenarioRunPayload } from '../types/scenario'

export const simulationService = {
  async create(payload: ScenarioRunPayload): Promise<Scenario> {
    const response = await api.post<Scenario>('/simulation/scenario', payload)
    return response.data
  },

  async list(datasetId: number): Promise<Scenario[]> {
    const response = await api.get<Scenario[]>(`/simulation/scenarios/${datasetId}`)
    return response.data
  },

  async compare(scenarioIds: number[]) {
    const response = await api.post('/simulation/compare', { scenario_ids: scenarioIds })
    return response.data
  },

  async sensitivity(payload: Record<string, unknown>) {
    const response = await api.post('/simulation/sensitivity', payload)
    return response.data
  },
}
