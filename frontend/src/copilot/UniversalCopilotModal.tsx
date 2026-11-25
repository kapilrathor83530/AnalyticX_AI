import {
  AlertTriangle,
  Bot,
  Camera,
  CheckCircle2,
  ChevronDown,
  Copy,
  Eye,
  Globe,
  HelpCircle,
  LoaderCircle,
  Maximize2,
  Minimize2,
  RefreshCw,
  Send,
  Sparkles,
  Square,
  Trash2,
  Wrench,
  X,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useLiveApplicationContext } from '../contexts/LiveApplicationContext'
import { useCopilotChat } from '../hooks/useCopilotChat'
import type { Citation, CopilotMessage, WorkspaceContext } from '../types/copilot'

interface Props {
  isOpen: boolean
  onClose: () => void
  context?: WorkspaceContext
  onActionExecuted?: () => void
}

export default function UniversalCopilotModal({
  isOpen,
  onClose,
  context,
  onActionExecuted,
}: Props) {
  const { state: liveState, explainCurrentScreen, analyzeVisualWorkspace } = useLiveApplicationContext()

  const {
    messages,
    setMessages,
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
    effectiveContext,
  } = useCopilotChat({
    defaultContext: context,
    onActionExecuted,
    storageKey: 'universal_modal',
  })

  const [isMinimized, setIsMinimized] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isOpen && typeof messagesEndRef.current?.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, loading, isStreaming, isOpen])

  if (!isOpen) return null

  async function handleExplainScreenClick() {
    try {
      const screenInfo = await explainCurrentScreen('Explain this screen and what I should do next', selectedLanguage)
      const assistantMsg: CopilotMessage = {
        id: `a_${Date.now()}`,
        role: 'assistant',
        content: `### 🖥️ Live Screen Intelligence: ${liveState.screen.screenName}\n\n${screenInfo.screen_summary}`,
        detected_language: screenInfo.language_name,
        verified_facts: screenInfo.key_observations,
        business_insights: screenInfo.warnings_or_issues.length
          ? screenInfo.warnings_or_issues
          : ['All displayed metrics are validated against backend database records.'],
        suggested_questions: screenInfo.recommended_next_steps,
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `err_${Date.now()}`,
          role: 'assistant',
          content: 'Unable to analyze screen right now. Please verify backend connection.',
        },
      ])
    }
  }

  async function handleVisualSnapshotClick() {
    try {
      const vis = await analyzeVisualWorkspace()
      const assistantMsg: CopilotMessage = {
        id: `a_${Date.now()}`,
        role: 'assistant',
        content: `### 📷 Visual Workspace Analysis\n\n${vis.explanation}\n\n**Layout Status:** \`${vis.layout_health}\`\n\n*${vis.numerical_grounding_note}*`,
        verified_facts: vis.visual_elements_detected,
        suggested_questions: vis.suggested_actions,
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `err_${Date.now()}`,
          role: 'assistant',
          content: 'Visual analysis could not be completed.',
        },
      ])
    }
  }

  function copyText(id: string, text: string) {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  return (
    <div
      className={`fixed bottom-4 right-4 z-50 flex flex-col rounded-3xl border border-cyan-500/30 bg-slate-950/95 shadow-2xl backdrop-blur-2xl transition-all duration-300 ${
        isMinimized ? 'h-16 w-80' : 'h-[640px] w-[460px] max-w-[calc(100vw-32px)]'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800/80 px-4 py-3 bg-gradient-to-r from-cyan-950/40 via-slate-900/60 to-slate-950">
        <div className="flex items-center gap-2.5">
          <div className="relative flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 text-slate-950 shadow-md shadow-cyan-500/20">
            <Sparkles size={16} />
            <span className="absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full bg-emerald-400 ring-2 ring-slate-950" />
          </div>
          <div>
            <div className="flex items-center gap-1.5 font-bold text-xs text-slate-100">
              <span>Analyticx Copilot</span>
              {detectedLanguage && detectedLanguage !== 'auto' && (
                <span className="rounded bg-cyan-400/20 px-1.5 py-0.2 text-[10px] text-cyan-300 font-medium uppercase tracking-wider">
                  {detectedLanguage}
                </span>
              )}
            </div>
            <div className="text-[10px] text-slate-400 truncate max-w-[200px]">
              {liveState.screen.screenName || 'Active Workspace'}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1">
          {/* Language Selector Dropdown */}
          <div className="relative group">
            <select
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              className="appearance-none rounded-lg border border-slate-700 bg-slate-900/90 pl-6 pr-5 py-1 text-[11px] text-slate-200 outline-none hover:border-cyan-400 focus:border-cyan-400 cursor-pointer"
              title="Select response language"
            >
              <option value="auto">🌐 Auto Detect</option>
              {languages.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.native || l.native_name || l.name} ({l.name})
                </option>
              ))}
            </select>
            <Globe size={11} className="absolute left-2 top-2 text-cyan-400 pointer-events-none" />
            <ChevronDown size={11} className="absolute right-1.5 top-2 text-slate-400 pointer-events-none" />
          </div>

          <button
            onClick={() => setIsMinimized((prev) => !prev)}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition"
            title={isMinimized ? 'Expand' : 'Minimize'}
          >
            {isMinimized ? <Maximize2 size={13} /> : <Minimize2 size={13} />}
          </button>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-red-300 transition"
            title="Close"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {!isMinimized && (
        <>
          {/* Real-time Screen Context Ribbon */}
          <div className="flex items-center justify-between border-b border-slate-800/60 bg-slate-900/40 px-3.5 py-1.5 text-[11px] text-slate-300">
            <div className="flex items-center gap-1.5 overflow-hidden">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 shrink-0" />
              <span className="truncate">
                {liveState.screen.screenName}
              </span>
              {effectiveContext.dataset_name && (
                <span className="text-cyan-200 truncate">
                  {effectiveContext.dataset_name}
                </span>
              )}
              {effectiveContext.dashboard_name && (
                <span className="text-slate-400 truncate">
                  {effectiveContext.dashboard_name}
                </span>
              )}
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <button
                onClick={handleExplainScreenClick}
                disabled={loading || isStreaming}
                className="flex items-center gap-1 rounded bg-slate-800 px-2 py-0.5 text-[10px] text-cyan-300 hover:bg-cyan-500/20 hover:text-cyan-200 transition disabled:opacity-40"
                title="Explain current screen content and recommendations"
              >
                <Eye size={10} />
                <span>Explain Screen</span>
              </button>
              <button
                onClick={handleVisualSnapshotClick}
                disabled={loading || isStreaming}
                className="flex items-center gap-1 rounded bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300 hover:bg-slate-700 hover:text-cyan-200 transition disabled:opacity-40"
                title="Capture screen layout analysis"
              >
                <Camera size={10} />
                <span>Visual Snapshot</span>
              </button>
            </div>
          </div>

          {/* Chat Messages Body */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3.5 text-xs text-slate-200">
            {messages.map((msg) => {
              const isUser = msg.role === 'user'
              return (
                <div key={msg.id} className={`flex gap-2.5 ${isUser ? 'justify-end' : 'justify-start'}`}>
                  {!isUser && (
                    <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-cyan-950 border border-cyan-800/50 text-cyan-400">
                      <Bot size={13} />
                    </div>
                  )}

                  <div
                    className={`group relative max-w-[85%] rounded-2xl p-3 leading-relaxed shadow-sm ${
                      isUser
                        ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white rounded-tr-none'
                        : 'bg-slate-900/90 border border-slate-800/80 text-slate-200 rounded-tl-none'
                    }`}
                  >
                    {/* Language tag for assistant */}
                    {!isUser && msg.detected_language && (
                      <div className="mb-1.5 flex items-center gap-1.5 text-[10px] text-cyan-400/80 font-medium">
                        <Globe size={10} />
                        <span>{msg.detected_language}</span>
                      </div>
                    )}

                    {/* Message content */}
                    <div className="whitespace-pre-wrap select-text font-normal">
                      {msg.content}
                      {msg.isStreaming && (
                        <span className="inline-block w-1.5 h-3.5 bg-cyan-400 animate-pulse ml-0.5 align-middle" />
                      )}
                    </div>

                    {/* Executed Action Badge */}
                    {msg.executed_action && (
                      <div className="mt-2.5 rounded-xl border border-emerald-500/30 bg-emerald-950/30 p-2 text-[11px] text-emerald-300 flex items-center gap-1.5">
                        <CheckCircle2 size={13} className="shrink-0 text-emerald-400" />
                        <span>
                          Action executed: <strong>{msg.executed_action.type}</strong>
                        </span>
                      </div>
                    )}

                    {/* Verified Facts & Statistics */}
                    {msg.verified_facts && msg.verified_facts.length > 0 && (
                      <div className="mt-2.5 space-y-1 rounded-xl bg-slate-950/60 p-2 border border-slate-800/80 text-[11px]">
                        <div className="font-semibold text-cyan-300 flex items-center gap-1 text-[10px] uppercase tracking-wider">
                          <CheckCircle2 size={11} />
                          <span>Verified Facts</span>
                        </div>
                        <ul className="list-disc pl-4 space-y-0.5 text-slate-300">
                          {msg.verified_facts.map((fact, idx) => (
                            <li key={idx}>{fact}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Business Insights */}
                    {msg.business_insights && msg.business_insights.length > 0 && (
                      <div className="mt-2 space-y-1 rounded-xl bg-amber-950/20 p-2 border border-amber-800/30 text-[11px]">
                        <div className="font-semibold text-amber-300 flex items-center gap-1 text-[10px] uppercase tracking-wider">
                          <Sparkles size={11} />
                          <span>Business Insights</span>
                        </div>
                        <ul className="list-disc pl-4 space-y-0.5 text-amber-100/90">
                          {msg.business_insights.map((ins, idx) => (
                            <li key={idx}>{ins}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* PDF Citations */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-2 space-y-1.5 rounded-xl bg-cyan-950/30 p-2 border border-cyan-800/40 text-[11px]">
                        <div className="font-semibold text-cyan-300 text-[10px] uppercase tracking-wider">
                          Source Citations (PDF)
                        </div>
                        {msg.citations.map((c: Citation, idx: number) => (
                          <div key={idx} className="rounded bg-slate-900/80 p-1.5 border border-slate-800">
                            <span className="font-bold text-cyan-400">Page {c.page}: </span>
                            <span className="text-slate-300 italic">"{c.snippet}"</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Copy action */}
                    <button
                      onClick={() => copyText(msg.id, msg.content)}
                      className="absolute right-2 top-2 hidden rounded p-1 text-slate-400 hover:text-slate-200 group-hover:block transition"
                      title="Copy message"
                    >
                      {copiedId === msg.id ? <CheckCircle2 size={12} className="text-emerald-400" /> : <Copy size={12} />}
                    </button>
                  </div>
                </div>
              )
            })}

            {loading && !isStreaming && (
              <div className="flex items-center gap-2.5 text-xs text-cyan-300 rounded-2xl bg-cyan-950/20 border border-cyan-800/30 px-3.5 py-2.5">
                <LoaderCircle size={15} className="animate-spin text-cyan-400" />
                <span>
                  Analyzing screen context in {selectedLanguage === 'auto' ? 'your detected language' : selectedLanguage}...
                </span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Suggested Questions */}
          {messages.length > 0 && messages[messages.length - 1].suggested_questions && (
            <div className="border-t border-slate-800/60 bg-slate-900/30 px-3 py-1.5 flex gap-1.5 overflow-x-auto no-scrollbar">
              {messages[messages.length - 1].suggested_questions!.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => sendMessage(q)}
                  disabled={loading || isStreaming}
                  className="shrink-0 rounded-full border border-slate-700 bg-slate-800/80 px-2.5 py-1 text-[11px] text-slate-300 hover:border-cyan-400 hover:text-cyan-200 transition disabled:opacity-40"
                >
                  {q}
                </button>
              ))}
            </div>
          )}

          {/* Input Box */}
          <div className="border-t border-slate-800/80 p-3 bg-slate-950">
            <div className="flex items-center gap-2">
              <input
                className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-cyan-400"
                placeholder="Ask about current screen, dataset, or commands like 'Duplicates hata do'..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') sendMessage()
                }}
                disabled={loading || isStreaming}
              />
              {isStreaming ? (
                <button
                  onClick={stopGenerating}
                  className="flex items-center gap-1 rounded-xl bg-amber-500/20 border border-amber-500/40 px-3 py-2 text-xs font-medium text-amber-200 hover:bg-amber-500/30 transition animate-pulse"
                  title="Stop Generating"
                >
                  <Square size={12} className="fill-amber-300" />
                  <span>Stop</span>
                </button>
              ) : (
                <button
                  onClick={() => sendMessage()}
                  disabled={loading || !input.trim()}
                  className="rounded-xl bg-gradient-to-r from-cyan-400 to-blue-500 p-2 text-slate-950 font-semibold hover:from-cyan-300 hover:to-blue-400 disabled:opacity-40 transition"
                  title="Send message"
                >
                  <Send size={15} />
                </button>
              )}
              <button
                onClick={clearMessages}
                className="rounded-xl border border-slate-800 p-2 text-slate-500 hover:text-slate-300 hover:bg-slate-900 transition"
                title="Clear chat"
              >
                <Trash2 size={15} />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
