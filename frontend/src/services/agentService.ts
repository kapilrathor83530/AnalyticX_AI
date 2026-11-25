import { api } from '../api/client'
import type { AgentQueryResponse, BusinessChatResponse } from '../types/agent'

export const agentService = {
  async query(datasetId: number, question: string, useLlm = true): Promise<AgentQueryResponse> {
    const response = await api.post<AgentQueryResponse>('/agents/query', {
      dataset_id: datasetId,
      question,
      use_llm: useLlm,
    })
    return response.data
  },

  async businessChat(datasetId: number, messages: { role: 'user' | 'assistant'; content: string }[]): Promise<BusinessChatResponse> {
    const response = await api.post<BusinessChatResponse>('/agents/business-chat', {
      dataset_id: datasetId,
      messages,
    }, {
      // CPU-only local LLM inference can take longer than the default API timeout.
      timeout: 120_000,
    })
    return response.data
  },
}
