import { api } from '../api/client'
import type { CopilotChatResponse, CopilotMessage, LanguageOption, WorkspaceContext } from '../types/copilot'

export interface StreamChatParams {
  messages: CopilotMessage[]
  context?: WorkspaceContext
  languageOverride?: string
  useLlm?: boolean
  signal?: AbortSignal
  onMetadata?: (meta: Partial<CopilotChatResponse>) => void
  onToken?: (token: string) => void
  onDone?: (data: Partial<CopilotChatResponse>) => void
  onError?: (err: Error) => void
}

export const copilotService = {
  async getLanguages(): Promise<LanguageOption[]> {
    const res = await api.get<LanguageOption[]>('/copilot/languages')
    return res.data
  },

  async chatWithCopilot(
    messages: CopilotMessage[],
    context?: WorkspaceContext,
    languageOverride = 'auto',
    useLlm = true,
  ): Promise<CopilotChatResponse> {
    const payload = {
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
      context,
      language: languageOverride,
      use_llm: useLlm,
    }
    const res = await api.post<CopilotChatResponse>('/copilot/chat', payload)
    return res.data
  },

  async streamChatWithCopilot({
    messages,
    context,
    languageOverride = 'auto',
    useLlm = true,
    signal,
    onMetadata,
    onToken,
    onDone,
    onError,
  }: StreamChatParams): Promise<void> {
    const payload = {
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
      context,
      language: languageOverride,
      use_llm: useLlm,
    }

    try {
      const response = await fetch('/api/v1/copilot/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal,
      })

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`)
      }

      if (!response.body) {
        throw new Error('ReadableStream not supported by browser response')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed.startsWith('data: ')) continue

          try {
            const data = JSON.parse(trimmed.slice(6))
            if (data.type === 'metadata' && onMetadata) {
              onMetadata(data)
            } else if (data.type === 'token' && onToken && typeof data.token === 'string') {
              onToken(data.token)
            } else if (data.type === 'done' && onDone) {
              onDone(data)
            }
          } catch {
            // Ignore partial SSE json lines
          }
        }
      }
    } catch (err: unknown) {
      if ((err as Error)?.name === 'AbortError') {
        // Stream aborted gracefully
        return
      }
      if (onError && err instanceof Error) {
        onError(err)
      } else {
        throw err
      }
    }
  },

  async askPdf(payload: {
    dataset_id?: number
    document_path?: string
    question: string
    page_number?: number
    language?: string
  }): Promise<{
    answer: string
    citations: Array<{ page: number; source_type: string; snippet: string; confidence: number }>
    verified_facts: string[]
    source_pages: number[]
    is_found: boolean
  }> {
    const res = await api.post('/copilot/pdf-ask', payload)
    return res.data
  },

  async getPdfPages(datasetId: number) {
    const res = await api.get(`/copilot/pdf/${datasetId}/pages`)
    return res.data
  },
}
