import { AlertTriangle, CheckCircle2, LoaderCircle, Send, Wrench } from 'lucide-react'
import { useState } from 'react'
import { agentService } from '../services/agentService'
import type { ChatMessage } from '../types/llm'
import type { BusinessChatResponse } from '../types/agent'
import MessageList from './MessageList'
import ChartRenderer from '../visualization-studio/ChartRenderer'

interface Props {
  context?: string
  datasetId?: number
  placeholder?: string
  disabled?: boolean
}

export default function AIChatPanel({ datasetId, placeholder, disabled }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [details, setDetails] = useState<BusinessChatResponse | null>(null)
  const [analysisStage, setAnalysisStage] = useState(0)

  const analysisStages = [
    'Understanding your business question…',
    'Inspecting relevant dataset columns…',
    'Calculating verified business metrics…',
    'Checking evidence and limitations…',
    'Preparing a decision-ready response…',
  ]

  async function send() {
    const text = input.trim()
    if (!text) return

    const next: ChatMessage[] = [...messages, { role: 'user', content: text }]
    setMessages(next)
    setInput('')
    setLoading(true)
    setError('')
    setAnalysisStage(0)
    const progressTimer = window.setInterval(() => {
      setAnalysisStage((current) => (current + 1) % analysisStages.length)
    }, 2200)

    try {
      if (!datasetId) throw new Error('Select a dataset before starting a business analysis chat.')
      const chatHistory = next
        .filter((message): message is ChatMessage & { role: 'user' | 'assistant' } => message.role !== 'system')
        .map(({ role, content }) => ({ role, content }))
      const response = await agentService.businessChat(datasetId, chatHistory)
      if (!response.available) {
        setError('Local LLM is not available. Deterministic analytics may still be available.')
      }
      setDetails(response)
      setMessages([...next, { role: 'assistant', content: response.answer }])
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to send message'
      setError(message.includes('timeout') ? 'The local model is taking longer than expected. Please try again in a moment.' : message)
    } finally {
      window.clearInterval(progressTimer)
      setLoading(false)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <p className="text-sm text-slate-500">Ask a business question about this dataset.</p>
        ) : (
          <MessageList messages={messages} />
        )}
        {loading && (
          <div className="mt-4 flex max-w-[85%] items-center gap-3 rounded-2xl border border-cyan-400/20 bg-cyan-400/5 px-4 py-3 text-sm text-cyan-100">
            <LoaderCircle size={17} className="animate-spin text-cyan-300" />
            <div>
              <div className="font-medium">Analyticx AI is analyzing</div>
              <div className="mt-0.5 text-xs text-cyan-200/70">{analysisStages[analysisStage]}</div>
            </div>
          </div>
        )}
        {details?.chart_config && datasetId ? (
        <div className="h-[300px] rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
          <ChartRenderer
            datasetId={datasetId}
            chartType={String(details.chart_config.chart_type || 'bar')}
            dataMapping={(details.chart_config.data_mapping || {}) as Record<string, string | string[]>}
            appearance={(details.chart_config.appearance || {}) as Record<string, unknown>}
            title={details.chart_config.title}
            aggregation={details.chart_config.aggregation}
          />
        </div>
      ) : null}
      {details && (
          <div className="mt-4 space-y-3 rounded-2xl border border-slate-700/80 bg-slate-950/50 p-3 text-xs">
            <div className="flex items-center gap-2 text-cyan-200"><Wrench size={14} /> Verified tools: {details.tools_used.join(', ') || 'none'}</div>
            {details.verified_facts.length > 0 && (
              <div>
                <div className="mb-1 flex items-center gap-1 font-medium text-emerald-200"><CheckCircle2 size={14} /> Verified facts</div>
                <ul className="list-disc space-y-1 pl-4 text-slate-300">{details.verified_facts.map((fact) => <li key={fact}>{fact}</li>)}</ul>
              </div>
            )}
            {details.limitations.length > 0 && (
              <div>
                <div className="mb-1 flex items-center gap-1 font-medium text-amber-200"><AlertTriangle size={14} /> Limits / assumptions</div>
                <ul className="list-disc space-y-1 pl-4 text-slate-300">{details.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
              </div>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="border-t border-red-500/30 bg-red-500/10 px-4 py-2 text-xs text-red-200">
          {error}
        </div>
      )}

      <div className="flex items-center gap-2 border-t border-slate-800 p-3">
        <input
          className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
          placeholder={placeholder || 'Ask a question...'}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') send()
          }}
          disabled={disabled || loading}
        />
        <button
          onClick={send}
          disabled={loading || disabled}
          className="rounded-xl bg-cyan-400 p-2 text-slate-950 hover:bg-cyan-300 disabled:opacity-50"
        >
          <Send size={16} />
        </button>
      </div>
      {details && (
        <div className="border-t border-slate-800 px-3 pb-3 text-xs text-slate-400">
          Try: {details.suggested_questions.map((question) => (
            <button key={question} className="mr-2 mt-2 rounded-lg border border-slate-700 px-2 py-1 text-left hover:border-cyan-400 hover:text-cyan-200" onClick={() => setInput(question)}>{question}</button>
          ))}
        </div>
      )}
    </div>
  )
}
