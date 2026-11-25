import {
  AlertTriangle,
  ArrowDownToLine,
  Check,
  Code2,
  Copy,
  FileQuestion,
  Info,
  Replace,
  Sparkles,
  Table2,
  X,
} from 'lucide-react'
import { useState } from 'react'
import type { SQLGenerationResponse } from '../../services/sqlStudioService'

interface Props {
  preview: SQLGenerationResponse
  onInsert: (sql: string, mode: 'append' | 'replace') => void
  onExplain: (sql: string) => void
  onClear: () => void
}

export default function AIQueryPreviewCard({
  preview,
  onInsert,
  onExplain,
  onClear,
}: Props) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(preview.sql)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'ranking':
        return 'bg-purple-500/10 text-purple-300 border-purple-500/30'
      case 'aggregation':
        return 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30'
      case 'time_series':
        return 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
      case 'data_quality':
        return 'bg-amber-500/10 text-amber-300 border-amber-500/30'
      case 'filter':
        return 'bg-blue-500/10 text-blue-300 border-blue-500/30'
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700'
    }
  }

  return (
    <div className="glass rounded-3xl p-5 border border-cyan-500/30 bg-slate-950/90 shadow-xl space-y-3.5 animate-in fade-in zoom-in-98 duration-150 relative">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-2.5">
        <div className="flex items-center gap-2">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-cyan-500/20 text-cyan-300 text-xs">
            <Sparkles size={12} />
          </span>
          <span className="text-xs font-bold uppercase tracking-wider text-slate-200">
            AI Generated Query Suggestion
          </span>
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase border ${getTypeColor(
              preview.query_type
            )}`}
          >
            {preview.query_type.replace('_', ' ')}
          </span>
        </div>

        <button
          onClick={onClear}
          title="Dismiss suggestion"
          className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800 transition"
        >
          <X size={14} />
        </button>
      </div>

      {/* Explanation text */}
      <div className="text-xs text-slate-300 flex items-start gap-2 bg-slate-900/60 p-2.5 rounded-xl border border-slate-800">
        <Info size={14} className="text-cyan-400 shrink-0 mt-0.5" />
        <span className="leading-relaxed">{preview.explanation}</span>
      </div>

      {/* SQL Code Block */}
      <div className="relative rounded-2xl border border-slate-800 bg-slate-950 p-3.5 font-mono text-xs text-cyan-200 overflow-x-auto shadow-inner">
        <pre className="whitespace-pre">{preview.sql}</pre>
      </div>

      {/* Columns & Assumptions Metadata */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400">
        <div className="flex flex-wrap items-center gap-2">
          {preview.columns_used.length > 0 && (
            <div className="flex items-center gap-1">
              <Table2 size={12} className="text-slate-500" />
              <span>Columns:</span>
              <span className="font-mono text-slate-300">
                {preview.columns_used.join(', ')}
              </span>
            </div>
          )}
        </div>

        {preview.assumptions.length > 0 && (
          <div className="flex items-center gap-1 text-slate-400">
            <span className="text-amber-400">•</span>
            <span>{preview.assumptions.join(' • ')}</span>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800/80">
        <div className="flex items-center gap-2">
          <button
            onClick={() => onExplain(preview.sql)}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:text-cyan-300 hover:border-cyan-500/40 transition"
          >
            <FileQuestion size={13} className="text-purple-400" />
            Explain Query
          </button>
          <button
            onClick={handleCopy}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:text-slate-100 hover:border-slate-700 transition"
          >
            {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
            {copied ? 'Copied' : 'Copy SQL'}
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onInsert(preview.sql, 'append')}
            title="Append below current query in editor"
            className="inline-flex items-center gap-1.5 rounded-xl border border-cyan-500/30 bg-cyan-500/10 px-3.5 py-1.5 text-xs font-semibold text-cyan-300 hover:bg-cyan-500/20 transition"
          >
            <ArrowDownToLine size={13} />
            Append to Editor
          </button>
          <button
            onClick={() => onInsert(preview.sql, 'replace')}
            title="Replace entire SQL editor content with this query"
            className="inline-flex items-center gap-1.5 rounded-2xl bg-cyan-400 px-4 py-1.5 text-xs font-bold text-slate-950 hover:bg-cyan-300 transition shadow-sm"
          >
            <Replace size={13} />
            Replace in Editor
          </button>
        </div>
      </div>
    </div>
  )
}
