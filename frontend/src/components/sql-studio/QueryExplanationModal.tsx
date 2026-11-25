import {
  AlertTriangle,
  CheckCircle2,
  Database,
  FileQuestion,
  Layers,
  Sparkles,
  Table2,
  X,
  Zap,
} from 'lucide-react'
import type { SQLExplanationResponse } from '../../services/sqlStudioService'

interface Props {
  isOpen: boolean
  onClose: () => void
  explanation: SQLExplanationResponse | null
  query: string
}

export default function QueryExplanationModal({
  isOpen,
  onClose,
  explanation,
  query,
}: Props) {
  if (!isOpen || !explanation) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="glass rounded-3xl border border-slate-700 bg-slate-950 p-6 max-w-xl w-full space-y-4 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <div className="rounded-xl bg-purple-500/10 p-2 text-purple-400 border border-purple-500/20">
              <FileQuestion size={18} />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-100">SQL Statement Explanation</h3>
              <p className="text-xs text-slate-400">
                Natural-language semantic breakdown of active query execution.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800 transition"
          >
            <X size={16} />
          </button>
        </div>

        {/* Narrative Explanation */}
        <div className="rounded-2xl border border-cyan-500/30 bg-cyan-950/20 p-4 text-xs text-cyan-200 leading-relaxed flex items-start gap-2.5">
          <Sparkles size={16} className="text-cyan-400 shrink-0 mt-0.5" />
          <span>{explanation.explanation}</span>
        </div>

        {/* Query Under Inspection */}
        <div className="space-y-1">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Query Code
          </span>
          <pre className="p-3 rounded-xl bg-slate-900 font-mono text-[11px] text-slate-300 overflow-x-auto max-h-28 border border-slate-800">
            {query}
          </pre>
        </div>

        {/* Breakdown Grid */}
        <div className="grid grid-cols-2 gap-2.5 text-xs">
          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
            <span className="text-[10px] font-semibold text-slate-400 uppercase flex items-center gap-1">
              <Table2 size={12} className="text-cyan-400" />
              Referenced Columns
            </span>
            <p className="text-slate-200 font-mono text-[11px] truncate">
              {explanation.columns_referenced.length > 0
                ? explanation.columns_referenced.join(', ')
                : 'All (*) / Expressions'}
            </p>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
            <span className="text-[10px] font-semibold text-slate-400 uppercase flex items-center gap-1">
              <Layers size={12} className="text-purple-400" />
              Aggregations
            </span>
            <p className="text-slate-200 font-mono text-[11px] truncate">
              {explanation.aggregations_used.length > 0
                ? explanation.aggregations_used.join(', ')
                : 'None (Raw Records)'}
            </p>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
            <span className="text-[10px] font-semibold text-slate-400 uppercase">
              Filtering & Grouping
            </span>
            <p className="text-slate-200 text-[11px]">
              {explanation.has_filters ? '✓ Active WHERE Filters' : 'No row filters'} ·{' '}
              {explanation.has_group_by ? '✓ GROUP BY' : 'No grouping'}
            </p>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
            <span className="text-[10px] font-semibold text-slate-400 uppercase">
              Sorting & Limits
            </span>
            <p className="text-slate-200 text-[11px]">
              {explanation.has_order_by ? '✓ ORDER BY' : 'Unsorted'} ·{' '}
              {explanation.limit ? `LIMIT ${explanation.limit}` : 'Sandbox default (500)'}
            </p>
          </div>
        </div>

        {/* Performance & Best Practice Notes */}
        {explanation.performance_notes.length > 0 && (
          <div className="space-y-1.5 pt-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1">
              <AlertTriangle size={12} />
              Performance & Optimizer Advice:
            </span>
            <div className="space-y-1 bg-slate-900/50 p-2.5 rounded-xl border border-slate-800 text-[11px] text-slate-400">
              {explanation.performance_notes.map((note, i) => (
                <div key={i} className="flex items-start gap-1.5">
                  <span className="text-amber-400">•</span>
                  <span>{note}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-end pt-3 border-t border-slate-800">
          <button
            onClick={onClose}
            className="rounded-xl px-4 py-2 text-xs font-semibold text-slate-400 hover:bg-slate-800 transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
