import {
  Bot,
  Check,
  ChevronDown,
  Copy,
  Eraser,
  Globe,
  LoaderCircle,
  MessageSquare,
  MessageSquarePlus,
  Send,
  Sparkles,
  Square,
  User,
  X,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useCopilotChat } from '../hooks/useCopilotChat'
import type { Citation } from '../types/copilot'

interface Props {
  dashboardId: number
  onClose: () => void
}

export default function DashboardChatPanel({ dashboardId, onClose }: Props) {
  const {
    messages,
    input,
    setInput,
    loading,
    isStreaming,
    languages,
    selectedLanguage,
    setSelectedLanguage,
    detectedLanguage,
    sendMessage,
    stopGenerating,
    clearMessages,
  } = useCopilotChat({
    storageKey: `dashboard_${dashboardId}`,
    defaultContext: {
      workspace_mode: 'Dashboard Studio',
      dashboard_id: dashboardId,
    },
    initialMessages: [
      {
        id: 'welcome',
        role: 'assistant',
        content:
          'Hello! I am your **Analyticx AI Dashboard Assistant**.\n\nYou can chat in **English, Hinglish, Hindi**, etc. Ask about your charts, filters, metrics, or ask *"Explain this screen"* or *"Are you able to see my second chart?"*',
        suggested_questions: [
          'Explain this screen',
          'Are you able to see my second chart?',
          'What are the key insights from this dashboard?',
          'Suggest next analytical step',
        ],
      },
    ],
  })

  const [copiedId, setCopiedId] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading, isStreaming])

  function handleCopy(id: string, text: string) {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const lastSuggestions =
    messages.length > 0
      ? messages[messages.length - 1].suggested_questions || []
      : [
          'Explain this screen',
          'Are you able to see my second chart?',
          'What are the key insights?',
        ]

  return (
    <aside className="fixed right-0 top-0 z-40 flex h-screen w-full sm:w-[390px] xl:w-[430px] flex-col overflow-hidden border-l border-slate-800 bg-slate-950/95 shadow-2xl backdrop-blur-xl transition-all duration-300">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3 bg-slate-900/40">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-cyan-500/20 text-cyan-400">
            <Sparkles size={16} />
          </div>
          <div>
            <div className="flex items-center gap-1.5 font-semibold text-xs text-slate-100">
              <span>Dashboard AI</span>
              {detectedLanguage && detectedLanguage !== 'auto' && (
                <span className="rounded bg-cyan-400/20 px-1.5 py-0.2 text-[9px] text-cyan-300 font-medium uppercase">
                  {detectedLanguage}
                </span>
              )}
            </div>
            <p className="text-[10px] text-slate-400">Active Visual Grounding</p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          {/* Language Selector */}
          <div className="relative">
            <select
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              className="appearance-none rounded-lg border border-slate-700 bg-slate-900 pl-5 pr-4 py-1 text-[10px] text-slate-200 outline-none hover:border-cyan-400 cursor-pointer"
            >
              <option value="auto">🌐 Auto</option>
              {languages.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.native || l.native_name || l.name}
                </option>
              ))}
            </select>
            <Globe size={10} className="absolute left-1.5 top-2 text-cyan-400 pointer-events-none" />
            <ChevronDown size={10} className="absolute right-1 top-2 text-slate-400 pointer-events-none" />
          </div>

          <button
            title="Clear conversation"
            onClick={clearMessages}
            className="rounded-lg p-1.5 hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
          >
            <Eraser size={14} />
          </button>
          <button
            title="Close"
            onClick={onClose}
            className="rounded-lg p-1.5 hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
          >
            <X size={15} />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3.5 text-xs text-slate-200">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`rounded-2xl p-3 space-y-2 border ${
              m.role === 'user'
                ? 'bg-cyan-950/40 border-cyan-800/40 ml-4'
                : 'bg-slate-900/60 border-slate-800/80 mr-4'
            }`}
          >
            <div className="flex items-center justify-between text-[10px] text-slate-400">
              <span className="flex items-center gap-1.5 font-medium">
                {m.role === 'user' ? (
                  <>
                    <User size={12} className="text-cyan-400" />
                    <span>You</span>
                  </>
                ) : (
                  <>
                    <Bot size={12} className="text-emerald-400" />
                    <span>Analyticx AI</span>
                  </>
                )}
              </span>
              <button
                onClick={() => handleCopy(m.id, m.content)}
                className="hover:text-slate-200 transition"
                title="Copy message"
              >
                {copiedId === m.id ? (
                  <Check size={12} className="text-emerald-400" />
                ) : (
                  <Copy size={12} />
                )}
              </button>
            </div>

            <div className="whitespace-pre-wrap leading-relaxed select-text font-sans">
              {m.content}
              {m.isStreaming && (
                <span className="inline-block w-1.5 h-3.5 bg-cyan-400 animate-pulse ml-0.5 align-middle" />
              )}
            </div>

            {/* Verified Facts */}
            {m.verified_facts && m.verified_facts.length > 0 && (
              <div className="pt-1.5 border-t border-slate-800/80 text-[11px]">
                <div className="text-[10px] uppercase font-semibold text-cyan-400 mb-1">
                  Verified Screen & Chart Facts
                </div>
                <ul className="list-disc pl-4 space-y-0.5 text-slate-300">
                  {m.verified_facts.map((fact, idx) => (
                    <li key={idx}>{fact}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Business Insights */}
            {m.business_insights && m.business_insights.length > 0 && (
              <div className="pt-1.5 border-t border-slate-800/80 text-[11px]">
                <div className="text-[10px] uppercase font-semibold text-amber-400 mb-1">
                  Business Observations
                </div>
                <ul className="list-disc pl-4 space-y-0.5 text-amber-100/90">
                  {m.business_insights.map((ins, idx) => (
                    <li key={idx}>{ins}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}

        {loading && !isStreaming && (
          <div className="rounded-2xl bg-slate-900 border border-slate-800 p-3 text-xs text-cyan-300 animate-pulse flex items-center gap-2">
            <LoaderCircle size={15} className="animate-spin text-cyan-400" />
            <span>Analyzing dashboard visuals…</span>
          </div>
        )}

        <div ref={endRef} />
      </div>

      {/* Suggested Prompt Pills */}
      <div className="border-t border-slate-800/80 bg-slate-900/30 p-2.5">
        <p className="text-[10px] text-slate-500 mb-1.5 px-1">Suggested questions:</p>
        <div className="flex flex-wrap gap-1.5">
          {lastSuggestions.map((s, idx) => (
            <button
              key={idx}
              onClick={() => sendMessage(s)}
              disabled={loading || isStreaming}
              className="rounded-lg border border-slate-800 bg-slate-900/80 px-2.5 py-1 text-[11px] text-cyan-200 hover:border-cyan-500/50 hover:bg-slate-800 transition disabled:opacity-40"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Input Form */}
      <form
        onSubmit={(e) => {
          e.preventDefault()
          sendMessage()
        }}
        className="border-t border-slate-800 p-3.5 bg-slate-950"
      >
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading || isStreaming}
            placeholder="Ask about your charts, metrics, or screen..."
            className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-cyan-400"
          />
          {isStreaming ? (
            <button
              type="button"
              onClick={stopGenerating}
              className="flex items-center gap-1 rounded-xl bg-amber-500/20 border border-amber-500/40 px-3 py-2 text-xs font-medium text-amber-200 hover:bg-amber-500/30 transition animate-pulse"
              title="Stop Generating"
            >
              <Square size={12} className="fill-amber-300" />
              <span>Stop</span>
            </button>
          ) : (
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="rounded-xl bg-gradient-to-r from-cyan-400 to-blue-500 p-2 text-slate-950 font-semibold hover:from-cyan-300 hover:to-blue-400 transition disabled:opacity-50"
              title="Send"
            >
              <Send size={15} />
            </button>
          )}
        </div>
      </form>
    </aside>
  )
}
