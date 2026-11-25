import { AlertCircle, Check, Copy, HelpCircle, Layers, Sliders, Sparkles } from 'lucide-react'
import { useState } from 'react'
import type { CleaningRecommendation } from '../types'

interface Props {
  recommendation: CleaningRecommendation
  onApply: (rec: CleaningRecommendation, chosenStrategy: string, customParam?: unknown) => Promise<void>
  onSkip: (recId: string) => void
}

export default function CleaningDecisionCard({ recommendation, onApply, onSkip }: Props) {
  const [selectedStrategy, setSelectedStrategy] = useState<string>(recommendation.recommended_action)
  const [customValue, setCustomValue] = useState<string>('')
  const [applying, setApplying] = useState(false)
  const [applied, setApplied] = useState(false)

  const severityBadge =
    recommendation.severity === 'high'
      ? 'border-rose-500/30 bg-rose-500/10 text-rose-300'
      : recommendation.severity === 'medium'
      ? 'border-amber-500/30 bg-amber-500/10 text-amber-300'
      : 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300'

  const issueTypeBadge =
    recommendation.issue_type === 'missing_values'
      ? 'bg-purple-500/10 text-purple-300 border-purple-500/30'
      : recommendation.issue_type === 'outliers'
      ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
      : recommendation.issue_type === 'duplicates'
      ? 'bg-rose-500/10 text-rose-300 border-rose-500/30'
      : 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30'

  async function handleApply() {
    setApplying(true)
    try {
      await onApply(recommendation, selectedStrategy, selectedStrategy === 'constant' ? customValue : undefined)
      setApplied(true)
    } finally {
      setApplying(false)
    }
  }

  if (applied) {
    return (
      <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/5 p-4 flex items-center justify-between transition-all">
        <div className="flex items-center gap-3">
          <div className="rounded-full bg-emerald-500/20 p-2 text-emerald-400">
            <Check size={18} />
          </div>
          <div>
            <p className="text-sm font-medium text-emerald-200">{recommendation.title}</p>
            <p className="text-xs text-slate-400">Action applied successfully using strategy: <span className="font-mono text-emerald-300">{selectedStrategy}</span></p>
          </div>
        </div>
        <span className="text-xs font-semibold text-emerald-400">Resolved</span>
      </div>
    )
  }

  const selectedAlt = recommendation.available_alternatives.find((a) => a.strategy === selectedStrategy)

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 space-y-4 hover:border-slate-700/80 transition-all">
      {/* Top Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2.5">
          <span className={`rounded-lg border px-2 py-0.5 text-[11px] font-medium uppercase tracking-wider ${issueTypeBadge}`}>
            {recommendation.issue_type.replace('_', ' ')}
          </span>
          <span className={`rounded-lg border px-2 py-0.5 text-[11px] font-medium capitalize ${severityBadge}`}>
            {recommendation.severity} severity
          </span>
          {recommendation.safe_for_auto && (
            <span className="hidden sm:inline-flex items-center gap-1 text-[11px] text-cyan-300/80">
              <Sparkles size={12} /> Auto-Safe
            </span>
          )}
        </div>
        <span className="text-xs text-slate-400">
          Impacts <strong className="text-slate-200">{recommendation.affected_count.toLocaleString()}</strong> rows ({recommendation.affected_percent}%)
        </span>
      </div>

      {/* Title & Explanation */}
      <div>
        <h3 className="text-base font-semibold text-slate-100">{recommendation.title}</h3>
        <p className="mt-1 text-xs leading-relaxed text-slate-400">{recommendation.why_it_matters}</p>
      </div>

      {/* Sample Values if any */}
      {recommendation.example_values && recommendation.example_values.length > 0 && (
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="shrink-0 text-slate-500">Sample values:</span>
          <div className="flex flex-wrap gap-1.5">
            {recommendation.example_values.slice(0, 4).map((val, i) => (
              <span key={i} className="rounded-md bg-slate-800 px-2 py-0.5 font-mono text-[11px] text-slate-300">
                {String(val)}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Strategy Selector & Controls */}
      <div className="rounded-xl border border-slate-800/90 bg-slate-950/40 p-3.5 space-y-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
            <Sliders size={13} className="text-cyan-400" />
            Select Resolution Strategy:
          </label>
          <select
            value={selectedStrategy}
            onChange={(e) => setSelectedStrategy(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 focus:border-cyan-400 outline-none"
          >
            {recommendation.available_alternatives.map((alt) => (
              <option key={alt.strategy} value={alt.strategy}>
                {alt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Selected strategy description */}
        {selectedAlt && (
          <p className="text-[11px] text-slate-400 italic">
            Effect: {selectedAlt.description}
          </p>
        )}

        {/* Custom value input if constant is selected */}
        {selectedStrategy === 'constant' && (
          <div className="flex items-center gap-2 pt-1">
            <input
              type="text"
              placeholder="Enter custom replacement value..."
              value={customValue}
              onChange={(e) => setCustomValue(e.target.value)}
              className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-cyan-400"
            />
          </div>
        )}
      </div>

      {/* Buttons */}
      <div className="flex items-center justify-between pt-1">
        <p className="text-[11px] text-slate-500">
          Expected: <span className="text-slate-300">{recommendation.expected_effect}</span>
        </p>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onSkip(recommendation.id)}
            className="rounded-xl border border-slate-800 px-3 py-1.5 text-xs text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition"
          >
            Skip
          </button>
          <button
            onClick={handleApply}
            disabled={applying}
            className="inline-flex items-center gap-1.5 rounded-xl bg-cyan-400 px-4 py-1.5 text-xs font-semibold text-slate-950 hover:bg-cyan-300 transition shadow-md shadow-cyan-950/40 disabled:opacity-50"
          >
            {applying ? 'Applying…' : 'Apply Decision'}
          </button>
        </div>
      </div>
    </div>
  )
}
