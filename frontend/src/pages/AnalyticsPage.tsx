import {
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  Download,
  FileSpreadsheet,
  FileText,
  RefreshCw,
  Table,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import Plot from 'react-plotly.js'
import { Link, useParams } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client'
import { reportService, triggerBrowserDownload } from '../services/reportService'
import type { EDA } from '../types'
import type { ExportFormat } from '../types/report'

export default function AnalyticsPage() {
  const { id } = useParams()
  const [eda, setEda] = useState<EDA | null>(null)
  const [error, setError] = useState('')
  const [downloadDropdownOpen, setDownloadDropdownOpen] = useState(false)
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null)
  const [downloadSuccess, setDownloadSuccess] = useState('')

  useEffect(() => {
    if (!id) return

    async function load() {
      try {
        const response = await api.get<EDA>(`/datasets/${id}/eda`)
        setEda(response.data)
      } catch (err) {
        setError(getErrorMessage(err))
      }
    }

    load()
  }, [id])

  const handleDownloadFullReport = async (format: ExportFormat) => {
    if (!id) return
    try {
      setDownloadingFormat(format)
      setDownloadDropdownOpen(false)
      const res = await reportService.generateReport({
        dataset_id: Number(id),
        report_type: 'statistical',
        export_format: format,
        title: `Statistical Profile - Dataset #${id}`,
      })
      await reportService.downloadSavedReport(
        res.report_id,
        `Analyticx_Statistical_Report_dataset_${id}.${format}`,
        format
      )
      setDownloadSuccess(`Downloaded complete statistical analysis report as ${format.toUpperCase()}.`)
      setTimeout(() => setDownloadSuccess(''), 4000)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setDownloadingFormat(null)
    }
  }

  const exportNumericSummaryCSV = () => {
    if (!eda?.numeric_summary) return
    const rows = [['Column', 'Mean', 'Std', 'Min', 'Max']]
    Object.entries(eda.numeric_summary).forEach(([col, s]) => {
      rows.push([col, String(s.mean ?? ''), String(s.std ?? ''), String(s.min ?? ''), String(s.max ?? '')])
    })
    const csvContent = rows.map((r) => r.map((c) => `"${c.replace(/"/g, '""')}"`).join(',')).join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    triggerBrowserDownload(blob, `Numeric_Summary_dataset_${id}.csv`)
  }

  if (error) {
    return <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-5 text-red-200">{error}</div>
  }

  if (!eda) {
    return <div className="text-slate-400">Loading analytics...</div>
  }

  const distributions = Object.entries(eda.numeric_distributions)

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <Link
          to={id ? `/datasets/${id}` : '/workspace'}
          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-xs text-cyan-300 transition hover:border-cyan-500/50 hover:bg-slate-800"
        >
          <ArrowLeft size={14} />
          Back to Dataset Studio
        </Link>

        {/* Download Statistical Report Action Bar */}
        <div className="relative flex items-center gap-3">
          <span className="text-xs text-slate-400 font-mono">Dataset #{id}</span>

          <div className="relative">
            <button
              onClick={() => setDownloadDropdownOpen(!downloadDropdownOpen)}
              disabled={downloadingFormat !== null}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-3.5 py-1.5 text-xs font-bold text-white shadow-lg shadow-cyan-500/20 hover:from-cyan-400 hover:to-blue-500 transition disabled:opacity-50"
            >
              {downloadingFormat ? (
                <RefreshCw size={13} className="animate-spin" />
              ) : (
                <Download size={13} />
              )}
              <span>
                {downloadingFormat ? `Generating ${downloadingFormat.toUpperCase()}...` : 'Download Analysis Report'}
              </span>
              <ChevronDown size={12} className={`transition-transform ${downloadDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {downloadDropdownOpen && (
              <div className="absolute right-0 top-full mt-2 z-50 w-64 rounded-2xl border border-slate-700 bg-slate-950 p-2 shadow-2xl backdrop-blur-xl animate-in fade-in zoom-in-95 duration-100">
                <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-800 mb-1">
                  Choose Export Format
                </div>
                <button
                  onClick={() => handleDownloadFullReport('pdf')}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-left text-xs text-slate-200 hover:bg-slate-800/80 transition"
                >
                  <FileText size={15} className="text-red-400 shrink-0" />
                  <div>
                    <div className="font-semibold">Executive PDF (.pdf)</div>
                    <div className="text-[10px] text-slate-400">Formatted executive analytics profile</div>
                  </div>
                </button>
                <button
                  onClick={() => handleDownloadFullReport('xlsx')}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-left text-xs text-slate-200 hover:bg-slate-800/80 transition"
                >
                  <FileSpreadsheet size={15} className="text-emerald-400 shrink-0" />
                  <div>
                    <div className="font-semibold">Excel Workbook (.xlsx)</div>
                    <div className="text-[10px] text-slate-400">Multi-tab moments, correlations, outliers</div>
                  </div>
                </button>
                <button
                  onClick={() => handleDownloadFullReport('docx')}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-left text-xs text-slate-200 hover:bg-slate-800/80 transition"
                >
                  <FileText size={15} className="text-blue-400 shrink-0" />
                  <div>
                    <div className="font-semibold">Word Document (.docx)</div>
                    <div className="text-[10px] text-slate-400">Editable documentation and tables</div>
                  </div>
                </button>
                <button
                  onClick={() => handleDownloadFullReport('csv')}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-left text-xs text-slate-200 hover:bg-slate-800/80 transition"
                >
                  <Table size={15} className="text-cyan-400 shrink-0" />
                  <div>
                    <div className="font-semibold">Tabular CSV (.csv)</div>
                    <div className="text-[10px] text-slate-400">Clean dataset snapshot & statistics</div>
                  </div>
                </button>
                <button
                  onClick={() => handleDownloadFullReport('json')}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-left text-xs text-slate-200 hover:bg-slate-800/80 transition"
                >
                  <FileText size={15} className="text-purple-400 shrink-0" />
                  <div>
                    <div className="font-semibold">Calculations JSON (.json)</div>
                    <div className="text-[10px] text-slate-400">Raw deterministic calculation payload</div>
                  </div>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {downloadSuccess && (
        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/20 p-3.5 text-xs text-emerald-200 flex items-center gap-2">
          <CheckCircle2 size={15} className="text-emerald-400 shrink-0" />
          <span>{downloadSuccess}</span>
        </div>
      )}

      <section className="grid gap-4 md:grid-cols-4">
        <Metric label="Rows" value={eda.row_count} />
        <Metric label="Columns" value={eda.column_count} />
        <Metric label="Duplicate Rows" value={eda.duplicate_rows} />
        <Metric label="Numeric Columns" value={Object.keys(eda.numeric_summary).length} />
      </section>

      <section className="glass rounded-3xl p-6">
        <div className="mb-5 flex items-center gap-3">
          <BarChart3 size={20} className="text-cyan-300" />
          <h2 className="text-xl font-semibold">Numeric Distributions</h2>
        </div>

        {distributions.length === 0 ? (
          <p className="text-sm text-slate-500">No numeric columns found.</p>
        ) : (
          <div className="grid gap-6 xl:grid-cols-2">
            {distributions.map(([column, distribution]) => (
              <div key={column} className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
                <h3 className="mb-3 font-medium">{column}</h3>
                <Plot
                  data={[
                    {
                      x: distribution.bins.slice(0, -1),
                      y: distribution.counts,
                      type: 'bar',
                      marker: { color: '#22d3ee' },
                    },
                  ]}
                  layout={{
                    autosize: true,
                    height: 280,
                    margin: { l: 40, r: 20, t: 10, b: 40 },
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#cbd5e1' },
                  }}
                  style={{ width: '100%' }}
                  config={{ displayModeBar: false, responsive: true }}
                />
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="glass rounded-3xl p-6">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Table size={20} className="text-cyan-300" />
            <h2 className="text-xl font-semibold">Numeric Summary</h2>
          </div>
          <button
            onClick={exportNumericSummaryCSV}
            title="Download Summary as CSV"
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:border-cyan-400 hover:text-cyan-300 transition"
          >
            <Download size={13} />
            Export Summary (CSV)
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[800px] text-left text-sm">
            <thead className="text-slate-400">
              <tr className="border-b border-slate-800">
                <th className="py-3">Column</th>
                <th className="py-3">Mean</th>
                <th className="py-3">Std</th>
                <th className="py-3">Min</th>
                <th className="py-3">Max</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(eda.numeric_summary).map(([column, summary]) => (
                <tr key={column} className="border-b border-slate-800/60">
                  <td className="py-3 font-medium">{column}</td>
                  <td className="py-3">{String(summary.mean ?? '—')}</td>
                  <td className="py-3">{String(summary.std ?? '—')}</td>
                  <td className="py-3">{String(summary.min ?? '—')}</td>
                  <td className="py-3">{String(summary.max ?? '—')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {(() => {
        const ext = eda as unknown as {
          categorical_breakdowns?: Record<string, Array<{ category: string; count: number; percentage: number }>>
          correlations?: Record<string, Record<string, number>>
          notable_correlations?: Array<{ col_a: string; col_b: string; pearson: number; spearman?: number; strength?: string; direction?: string }>
          time_trends?: { date_column: string; target_column: string; labels: string[]; values: number[] } | null
        }
        const catEntries = Object.entries(ext.categorical_breakdowns || {})
        const corrCols = Object.keys(ext.correlations || {})
        const trend = ext.time_trends
        return (
          <>
            {catEntries.length > 0 ? (
              <section className="glass rounded-2xl p-6 space-y-4">
                <h2 className="text-lg font-semibold">Categorical Breakdowns</h2>
                <div className="grid gap-6 md:grid-cols-2">
                  {catEntries.slice(0, 6).map(([col, items]) => (
                    <div key={col} className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-4">
                      <p className="mb-3 text-sm font-semibold text-cyan-300">{col}</p>
                      <div className="space-y-2">
                        {items.slice(0, 8).map((item) => (
                          <div key={item.category} className="space-y-1">
                            <div className="flex justify-between text-xs text-slate-300">
                              <span className="truncate pr-2">{item.category}</span>
                              <span className="text-slate-400">{item.count} ({item.percentage}%)</span>
                            </div>
                            <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
                              <div className="h-full rounded-full bg-cyan-400" style={{ width: `${Math.min(100, Math.max(2, item.percentage))}%` }} />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            ) : null}

            {corrCols.length >= 2 ? (
              <section className="glass rounded-2xl p-6 space-y-4">
                <h2 className="text-lg font-semibold">Correlation Matrix (Pearson)</h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400">
                        <th className="py-2 pr-3">Feature</th>
                        {corrCols.map((col) => (
                          <th key={col} className="px-2 py-2 text-center">{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {corrCols.map((rowCol) => (
                        <tr key={rowCol} className="border-b border-slate-800/50">
                          <td className="py-2 pr-3 font-medium text-slate-200">{rowCol}</td>
                          {corrCols.map((colCol) => {
                            const val = ext.correlations?.[rowCol]?.[colCol] ?? 0
                            const abs = Math.abs(val)
                            const bg = val >= 0
                              ? `rgba(34, 211, 238, ${0.12 + abs * 0.45})`
                              : `rgba(251, 113, 133, ${0.12 + abs * 0.45})`
                            return (
                              <td key={colCol} className="px-2 py-2 text-center font-mono text-slate-100" style={{ backgroundColor: bg }}>
                                {val.toFixed(2)}
                              </td>
                            )
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {ext.notable_correlations && ext.notable_correlations.length > 0 ? (
                  <p className="text-xs text-slate-400">
                    Top association: {ext.notable_correlations[0].col_a} &amp; {ext.notable_correlations[0].col_b} (r = {ext.notable_correlations[0].pearson}, observational correlation only).
                  </p>
                ) : null}
              </section>
            ) : null}

            {trend && trend.labels && trend.labels.length > 1 ? (
              <section className="glass rounded-2xl p-6 space-y-3">
                <h2 className="text-lg font-semibold">
                  Temporal Trend: {trend.target_column} over {trend.date_column}
                </h2>
                <div className="flex items-end gap-1.5 h-32 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
                  {(() => {
                    const maxV = Math.max(...trend.values, 1)
                    const minV = Math.min(...trend.values, 0)
                    const span = Math.max(maxV - minV, 1)
                    return trend.values.slice(-30).map((val, idx) => {
                      const pct = Math.max(8, Math.round(((val - minV) / span) * 100))
                      const label = trend.labels.slice(-30)[idx] || ''
                      return (
                        <div key={`${label}-${idx}`} className="flex flex-1 flex-col items-center justify-end h-full" title={`${label}: ${val}`}>
                          <div className="w-full rounded-t bg-emerald-400/80" style={{ height: `${pct}%` }} />
                        </div>
                      )
                    })
                  })()}
                </div>
              </section>
            ) : null}
          </>
        )
      })()}
    </div>
  )
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="glass rounded-2xl p-5">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-2 text-3xl font-semibold">{value}</p>
    </div>
  )
}
