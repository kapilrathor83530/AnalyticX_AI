import { useCallback, useEffect, useRef, useState } from 'react'
import { useLiveApplicationContext } from '../contexts/LiveApplicationContext'
import { copilotService } from '../services/copilotService'
import type { CopilotChatResponse, CopilotMessage, LanguageOption, WorkspaceContext } from '../types/copilot'

interface UseCopilotChatOptions {
  initialMessages?: CopilotMessage[]
  defaultContext?: WorkspaceContext
  onActionExecuted?: () => void
  storageKey?: string
}

export function useCopilotChat({
  initialMessages = [],
  defaultContext,
  onActionExecuted,
  storageKey,
}: UseCopilotChatOptions = {}) {
  const { state: liveState, explainCurrentScreen } = useLiveApplicationContext()

  const [messages, setMessages] = useState<CopilotMessage[]>(() => {
    if (storageKey) {
      try {
        const saved = sessionStorage.getItem(`copilot_chat_${storageKey}`)
        if (saved) return JSON.parse(saved)
      } catch {
        // Fallback to initial
      }
    }
    return initialMessages.length > 0
      ? initialMessages
      : [
          {
            id: 'welcome',
            role: 'assistant',
            content:
              'Hello! I am **Analyticx AI Multilingual Copilot**.\n\nYou can chat with me naturally in **English, Hinglish (Roman Hindi), Hindi (हिन्दी), Punjabi (ਪੰਜਾਬੀ), Bengali, Tamil**, and more.\n\nAsk business questions, analyze PDFs with page citations, ask about your current screen (e.g. *"What am I working on?"*), or instruct me to clean data directly (e.g. *"duplicates hata do"*, *"missing values median se fill karo"*).',
            suggested_questions: [
              'Explain this screen',
              'What should I do next?',
              'Is dataset ka EDA summary dikhao',
              'Duplicates hata do',
            ],
          },
        ]
  })

  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [languages, setLanguages] = useState<LanguageOption[]>([])
  const [selectedLanguage, setSelectedLanguage] = useState<string>('auto')
  const [detectedLanguage, setDetectedLanguage] = useState<string>('auto')
  const [error, setError] = useState<string | null>(null)

  const abortControllerRef = useRef<AbortController | null>(null)

  // Persist conversation if storageKey provided
  useEffect(() => {
    if (storageKey && messages.length > 0) {
      try {
        sessionStorage.setItem(`copilot_chat_${storageKey}`, JSON.stringify(messages))
      } catch {
        // Ignore storage errors
      }
    }
  }, [messages, storageKey])

  useEffect(() => {
    copilotService.getLanguages().then(setLanguages).catch(() => {})
  }, [])

  const effectiveContext: WorkspaceContext = {
    workspace_mode: defaultContext?.workspace_mode || liveState.screen.screenName,
    dataset_id: defaultContext?.dataset_id || liveState.dataset.datasetId || undefined,
    dataset_name: defaultContext?.dataset_name || liveState.dataset.datasetName || undefined,
    document_id: defaultContext?.document_id || (liveState.file.fileId ? String(liveState.file.fileId) : undefined),
    page_number: defaultContext?.page_number || liveState.file.pdfPageNumber || undefined,
    selected_column: defaultContext?.selected_column || liveState.dataset.focusedColumn || undefined,
    dashboard_id: defaultContext?.dashboard_id || liveState.dashboard.dashboardId || undefined,
    dashboard_name: defaultContext?.dashboard_name || liveState.dashboard.dashboardName || undefined,
    widget_id: defaultContext?.widget_id || liveState.dashboard.selectedWidgetId || undefined,
    chart_type: defaultContext?.chart_type || liveState.dashboard.selectedChartType || undefined,
    active_filters: defaultContext?.active_filters || liveState.dashboard.activeFilters,
    language_override: selectedLanguage,
  }

  const stopGenerating = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setIsStreaming(false)
    setLoading(false)
    setMessages((prev) =>
      prev.map((msg) => (msg.isStreaming ? { ...msg, isStreaming: false } : msg))
    )
  }, [])

  const sendMessage = useCallback(
    async (textToSend?: string) => {
      const text = (textToSend ?? input).trim()
      if (!text || loading || isStreaming) return

      setError(null)
      const userMsg: CopilotMessage = {
        id: `u_${Date.now()}`,
        role: 'user',
        content: text,
      }

      const updated = [...messages, userMsg]
      setMessages(updated)
      setInput('')
      setLoading(true)

      const qLower = text.toLowerCase()
      const isScreenQuestion =
        qLower.includes('explain this screen') ||
        qLower.includes('what am i working on') ||
        qLower.includes('what does this page show') ||
        qLower.includes('what should i do next') ||
        qLower.includes('is screen ko explain') ||
        qLower.includes('is page pe kya chal raha') ||
        qLower.includes('current status of my analysis') ||
        qLower.includes('see this screen') ||
        qLower.includes('see this completely screen') ||
        qLower.includes('see this entire screen') ||
        qLower.includes('see my screen') ||
        qLower.includes('able to see') ||
        qLower.includes('can you see') ||
        qLower.includes('visible on screen') ||
        qLower.includes('second chart') ||
        qLower.includes('2nd chart') ||
        qLower.includes('see my chart')

      if (isScreenQuestion) {
        try {
          const screenInfo = await explainCurrentScreen(text, selectedLanguage)
          const assistantMsg: CopilotMessage = {
            id: `a_${Date.now()}`,
            role: 'assistant',
            content: screenInfo.screen_summary,
            detected_language: screenInfo.language_name,
            verified_facts: screenInfo.key_observations,
            business_insights: screenInfo.warnings_or_issues.length
              ? screenInfo.warnings_or_issues
              : ['Screen state synchronized via Live Application Context Engine.'],
            suggested_questions: screenInfo.recommended_next_steps,
          }
          setMessages((prev) => [...prev, assistantMsg])
          setLoading(false)
          return
        } catch {
          // Fall back to streaming copilot
        }
      }

      const assistantId = `a_${Date.now()}`
      const placeholderMsg: CopilotMessage = {
        id: assistantId,
        role: 'assistant',
        content: '',
        isStreaming: true,
      }

      setMessages((prev) => [...prev, placeholderMsg])
      setIsStreaming(true)

      const controller = new AbortController()
      abortControllerRef.current = controller

      try {
        await copilotService.streamChatWithCopilot({
          messages: updated,
          context: effectiveContext,
          languageOverride: selectedLanguage,
          useLlm: true,
          signal: controller.signal,
          onMetadata: (meta: Partial<CopilotChatResponse>) => {
            if (meta.detected_language) {
              setDetectedLanguage(meta.detected_language)
            }
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      detected_language: meta.detected_language || m.detected_language,
                      citations: meta.citations || m.citations,
                      verified_facts: meta.verified_facts || m.verified_facts,
                      business_insights: meta.business_insights || m.business_insights,
                      executed_action: meta.executed_action || m.executed_action,
                    }
                  : m
              )
            )
            if (meta.executed_action && onActionExecuted) {
              onActionExecuted()
            }
          },
          onToken: (token: string) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + token, isStreaming: true }
                  : m
              )
            )
          },
          onDone: (data: Partial<CopilotChatResponse>) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      isStreaming: false,
                      suggested_questions: data.suggested_questions || m.suggested_questions,
                      business_insights: data.business_insights || m.business_insights,
                    }
                  : m
              )
            )
            setIsStreaming(false)
            setLoading(false)
            abortControllerRef.current = null
          },
          onError: (err: Error) => {
            setError(err.message || 'Error communicating with assistant')
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      content:
                        m.content.trim() ||
                        `⚠️ Error: ${err.message || 'Request failed. Please retry.'}`,
                      isStreaming: false,
                    }
                  : m
              )
            )
            setIsStreaming(false)
            setLoading(false)
            abortControllerRef.current = null
          },
        })
      } catch (err: unknown) {
        const errorMsg = err instanceof Error ? err.message : 'Chat error'
        setError(errorMsg)
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content:
                    m.content.trim() ||
                    `⚠️ Error: ${errorMsg}. Please try again.`,
                  isStreaming: false,
                }
              : m
          )
        )
      } finally {
        setIsStreaming(false)
        setLoading(false)
        abortControllerRef.current = null
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [input, loading, isStreaming, messages, selectedLanguage, effectiveContext, onActionExecuted, explainCurrentScreen]
  )

  const clearMessages = useCallback(() => {
    stopGenerating()
    setMessages([])
    setError(null)
    if (storageKey) {
      try {
        sessionStorage.removeItem(`copilot_chat_${storageKey}`)
      } catch {
        // Ignore
      }
    }
  }, [stopGenerating, storageKey])

  return {
    messages,
    setMessages,
    input,
    setInput,
    loading,
    isStreaming,
    error,
    languages,
    selectedLanguage,
    setSelectedLanguage,
    detectedLanguage,
    sendMessage,
    stopGenerating,
    clearMessages,
    effectiveContext,
  }
}
