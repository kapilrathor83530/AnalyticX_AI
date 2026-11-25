import {
  HelpCircle,
  Lightbulb,
  Loader2,
  RefreshCw,
  Sparkles,
  Zap,
} from 'lucide-react'
import { useState } from 'react'
import type { SQLSuggestionItem } from '../../services/sqlStudioService'

interface Props {
  prompt: string
  setPrompt: (value: string) => void
  onGenerate: () => void
  loading: boolean
  autoSuggest: boolean
  setAutoSuggest: (val: boolean) => void
  suggestions: SQLSuggestionItem[]
  onSelectSuggestion: (s: SQLSuggestionItem) => void
  clarifyingQuestions?: string[]
}

export default function NaturalLanguageSQLBar({
  prompt,
  setPrompt,
  onGenerate,
  loading,
  autoSuggest,
  setAutoSuggest,
  suggestions,
  onSelectSuggestion,
  clarifyingQuestions = [],
}: Props) {
  const [showHelperTips, setShowHelperTips] = useState(false)

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey || !autoSuggest)) {
      e.preventDefault()
      onGenerate()
    }
  }

  return (
    <div className="glass rounded-3xl p-5 border border-slate-800 space-y-3.5 bg-gradient-to-br from-slate-950/80 via-slate-900/60 to-slate-950">
      {/* Top row: Label & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="rounded-xl bg-cyan-500/10 p-1.5 border border-cyan-500/30 text-cyan-400">
            <Sparkles size={16} />
          </div>
          <div>
            <label htmlFor="nl-sql-input" className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Describe what you want to query
            </label>
            <p className="text-[11px] text-slate-400">
              Converts plain English into schema-grounded, executable SQLite statements.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs">
          {/* Auto-suggest toggle */}
          <label className="flex items-center gap-1.5 cursor-pointer text-slate-400 hover:text-slate-200 transition select-none">
            <input
              type="checkbox"
              checked={autoSuggest}
              onChange={(e) => setAutoSuggest(e.target.checked)}
              className="rounded border-slate-700 bg-slate-900 text-cyan-400 focus:ring-0 h-3.5 w-3.5"
            />
            <span className="text-[11px]">Auto-suggest as you type</span>
          </label>

          <button
            type="button"
            onClick={() => setShowHelperTips(!showHelperTips)}
            className="text-slate-400 hover:text-cyan-300 transition"
            title="Show natural language prompt examples"
          >
            <HelpCircle size={15} />
          </button>
        </div>
      </div>

      {/* Main Input Row */}
      <div className="relative flex items-center gap-2">
        <div className="relative flex-1">
          <input
            id="nl-sql-input"
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Example: Show the top 10 products by total sales, or average profit by region..."
            className="w-full rounded-2xl border border-slate-800 bg-slate-950/90 px-4 py-3 text-xs text-slate-100 placeholder-slate-500 shadow-inner focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400/50 pr-20"
          />
          {prompt && (
            <button
              onClick={() => setPrompt('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-[10px] font-mono px-1 py-0.5"
            >
              CLEAR
            </button>
          )}
        </div>

        <button
          onClick={onGenerate}
          disabled={loading || !prompt.trim()}
          title="Generate SQL statement (Ctrl + Enter)"
          className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 px-5 py-3 text-xs font-bold text-white shadow-lg shadow-cyan-500/20 hover:from-cyan-400 hover:to-blue-500 transition disabled:opacity-50 shrink-0"
        >
          {loading ? (
            <Loader2 size={15} className="animate-spin" />
          ) : (
            <Sparkles size={15} />
          )}
          <span>{loading ? 'Synthesizing...' : 'Generate SQL'}</span>
          <span className="hidden sm:inline-block rounded bg-cyan-900/50 px-1.5 py-0.5 text-[9px] font-mono text-cyan-200">
            Ctrl+↵
          </span>
        </button>
      </div>

      {/* Ambiguity or Clarification Alerts */}
      {clarifyingQuestions.length > 0 && (
        <div className="rounded-2xl border border-amber-500/30 bg-amber-950/20 p-3 text-xs text-amber-200 space-y-1">
          <div className="font-semibold flex items-center gap-1.5">
            <Lightbulb size={13} className="text-amber-400" />
            Clarification Notice:
          </div>
          <ul className="list-disc pl-5 space-y-0.5 text-[11px] text-amber-300/90">
            {clarifyingQuestions.map((cq, i) => (
              <li key={i}>{cq}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Helper Tips Expandable */}
      {showHelperTips && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-3.5 text-xs text-slate-300 space-y-2 animate-in fade-in duration-150">
          <p className="font-semibold text-cyan-300 text-[11px] uppercase tracking-wider">
            Natural Language Patterns Supported:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 text-[11px]">
            <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <span className="font-mono text-cyan-300">"top 10 {`{category}`} by {`{metric}`}"</span>
              <p className="text-slate-400 text-[10px] mt-0.5">Ranks entities by sum/avg.</p>
            </div>
            <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <span className="font-mono text-cyan-300">"monthly trend of {`{metric}`}"</span>
              <p className="text-slate-400 text-[10px] mt-0.5">Groups over chronology via strftime.</p>
            </div>
            <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <span className="font-mono text-cyan-300">"find duplicates in {`{column}`}"</span>
              <p className="text-slate-400 text-[10px] mt-0.5">Identifies repeated occurrences.</p>
            </div>
            <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <span className="font-mono text-cyan-300">"audit missing values"</span>
              <p className="text-slate-400 text-[10px] mt-0.5">Sums null occurrences across cols.</p>
            </div>
            <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <span className="font-mono text-cyan-300">"{`{metric}`} above {`{value}`}"</span>
              <p className="text-slate-400 text-[10px] mt-0.5">Numerical threshold filter.</p>
            </div>
            <div className="p-2 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <span className="font-mono text-cyan-300">"count total records"</span>
              <p className="text-slate-400 text-[10px] mt-0.5">Instant dataset row count.</p>
            </div>
          </div>
        </div>
      )}

      {/* Context-Aware Query Suggestions Chips */}
      {suggestions.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <span className="text-[11px] font-semibold text-slate-400 flex items-center gap-1 mr-1">
            <Zap size={12} className="text-cyan-400" />
            Recommended for this schema:
          </span>
          {suggestions.slice(0, 5).map((s, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => onSelectSuggestion(s)}
              className="rounded-xl border border-slate-800 bg-slate-900/90 hover:border-cyan-500/40 hover:bg-slate-800/90 px-2.5 py-1 text-[11px] font-medium text-slate-300 hover:text-cyan-200 transition shadow-sm"
              title={s.sql}
            >
              {s.title}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
