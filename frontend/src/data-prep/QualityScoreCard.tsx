import { AlertTriangle, CheckCircle2, ChevronRight, Download, FileSpreadsheet, FileText, RotateCcw, Sparkles } from 'lucide-react'
import type { QualityReport } from '../types'

interface Props {
  qualityReport: QualityReport
  onAutoClean: () => void
  onUndo: () => void
  autoCleaning: boolean
  hasTransformations: boolean
  onExport: (format: 'csv' | 'xlsx' | 'log' | 'report') => void
}

export default function QualityScoreCard({
  qualityReport,
  onAutoClean,
  onUndo,
  autoCleaning,
  hasTransformations,
  onExport,
}: Props) {
  const score = qualityReport.quality_score
  const scoreColor =
    score >= 80 ? 'text-emerald-400' : score >= 50 ? 'text-amber-400' : 'text-rose-400'
  const badgeBg =
    score >= 80 ? 'bg-emerald-500/10 border-emerald-500/30' : score >= 50 ? 'bg-amber-500/10 border-amber-500/30' : 'bg-rose-500/10 border-rose-500/30'

  const { summary } = qualityReport

  return (
    <div className="glass rounded-3xl p-6 space-y-6">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        {/* Quality Score Visual */}
        <div className="flex items-center gap-5">
          <div className={`relative flex h-20 w-20 shrink-0 items-center justify-center rounded-2xl border ${badgeBg}`}>
            <span className={`text-3xl font-bold tracking-tight ${scoreColor}`}>{score}%</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-semibold text-slate-100">Data Quality & Health Index</h2>
              <span className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${badgeBg} ${scoreColor}`}>
                {score >= 80 ? 'Analysis Ready' : score >= 50 ? 'Needs Attention' : 'Critical Issues'}
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-400 max-w-xl">
              Calculated from missing value density, duplicate records, statistical outlier distribution, and field variance.
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {hasTransformations && (
            <button
              onClick={onUndo}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900/80 px-3.5 py-2 text-xs font-medium text-slate-300 hover:border-slate-500 hover:text-white transition"
              title="Undo last cleaning operation"
            >
              <RotateCcw size={15} />
              Undo Last Action
            </button>
          )}

          <button
            onClick={onAutoClean}
            disabled={autoCleaning || qualityReport.recommendations.length === 0}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-teal-400 px-5 py-2 text-xs font-semibold text-slate-950 shadow-lg shadow-cyan-950/50 hover:brightness-110 transition disabled:opacity-50"
          >
            <Sparkles size={16} />
            {autoCleaning ? 'Applying Auto-Clean…' : 'Intelligent Auto-Clean All'}
          </button>

          {/* Export options */}
          <div className="flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/60 p-1">
            <button
              onClick={() => onExport('csv')}
              className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs text-slate-300 hover:bg-slate-800 hover:text-cyan-300 transition"
              title="Download Cleaned CSV"
            >
              <Download size={13} />
              CSV
            </button>
            <button
              onClick={() => onExport('xlsx')}
              className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs text-slate-300 hover:bg-slate-800 hover:text-cyan-300 transition"
              title="Download Cleaned Excel Workbook"
            >
              <FileSpreadsheet size={13} />
              Excel
            </button>
            <button
              onClick={() => onExport('log')}
              className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs text-slate-300 hover:bg-slate-800 hover:text-cyan-300 transition"
              title="Download Transformation Audit Log"
            >
              Log
            </button>
            <button
              onClick={() => onExport('report')}
              className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs text-slate-300 hover:bg-slate-800 hover:text-cyan-300 transition"
              title="Download Complete Statistical Profile Report (PDF)"
            >
              <FileText size={13} />
              Statistical PDF
            </button>
          </div>
        </div>
      </div>

      {/* Summary KPI Pills */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-5">
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-3.5">
          <p className="text-[11px] font-medium text-slate-400">Total Rows</p>
          <p className="mt-1 text-lg font-semibold text-slate-200">{qualityReport.dataset_shape.rows.toLocaleString()}</p>
        </div>
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-3.5">
          <p className="text-[11px] font-medium text-slate-400">Columns Profiled</p>
          <p className="mt-1 text-lg font-semibold text-slate-200">{qualityReport.dataset_shape.columns}</p>
        </div>
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-3.5">
          <p className="text-[11px] font-medium text-slate-400">Missing Cells</p>
          <p className={`mt-1 text-lg font-semibold ${summary.total_missing_cells > 0 ? 'text-amber-300' : 'text-emerald-400'}`}>
            {summary.total_missing_cells.toLocaleString()} <span className="text-xs font-normal text-slate-400">({summary.missing_cells_pct}%)</span>
          </p>
        </div>
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-3.5">
          <p className="text-[11px] font-medium text-slate-400">Duplicate Rows</p>
          <p className={`mt-1 text-lg font-semibold ${summary.duplicate_rows > 0 ? 'text-rose-300' : 'text-emerald-400'}`}>
            {summary.duplicate_rows.toLocaleString()}
          </p>
        </div>
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-3.5 col-span-2 sm:col-span-1">
          <p className="text-[11px] font-medium text-slate-400">Outlier Columns</p>
          <p className={`mt-1 text-lg font-semibold ${summary.columns_with_outliers > 0 ? 'text-amber-300' : 'text-slate-200'}`}>
            {summary.columns_with_outliers}
          </p>
        </div>
      </div>
    </div>
  )
}
