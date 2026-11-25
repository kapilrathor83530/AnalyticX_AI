import { api } from '../api/client'
import type { ChatMessage, ChatResponse, CommandResponse, ModelStatus } from '../types/llm'

export const llmService = {
  async status(): Promise<ModelStatus> {
    const response = await api.get<ModelStatus>('/llm/health')
    return response.data
  },

  async listModels(): Promise<string[]> {
    const response = await api.get<{ models: string[] }>('/llm/models')
    return response.data.models
  },

  async chat(messages: ChatMessage[], context?: string): Promise<ChatResponse> {
    const response = await api.post<ChatResponse>('/llm/chat', { messages, context })
    return response.data
  },

  async command(datasetId: number, command: string): Promise<CommandResponse> {
    const response = await api.post<CommandResponse>('/llm/command', {
      dataset_id: datasetId,
      command,
    })
    return response.data
  },
}
