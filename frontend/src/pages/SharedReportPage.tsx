import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  Check,
  CheckCircle2,
  Copy,
  Download,
  FileSpreadsheet,
  FileText,
  Lightbulb,
  Printer,
  Share2,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client'

interface SharedReportData {
  share_token: string
  dataset_id: number
  dataset_name: string
  title: string
  generated_at: string
  executive_summary?: string
  root_cause_data?: {
    metric_column: string
    primary_driver_dimension: string
    total_delta: number
    percent_change: number
    direction: string
    baseline_value: number
    comparison_value: number
    waterfall_steps?: { name: string; value: number; type: string; contribution_share?: number }[]
  }
  sections: Array<{
    title: string
    text?: string
    rows?: Record<string, unknown>[]
  }>
  recommendations: string[]
}

export default function SharedReportPage() {
  const { token } = useParams()
  const [report, setReport] = useState<SharedReportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!token) return
    api
      .get<SharedReportData>(`/reports/shared/${token}`)
      .then((res) => setReport(res.data))
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [token])

  function handleCopyLink() {
    navigator.clipboard.writeText(window.location.href)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  function handlePrint() {
    window.print()
  }

  async function downloadFormat(fmt: 'pdf' | 'docx' | 'pptx') {
    if (!report) return
    try {
      const res = await api.post(
        `/reports/dataset/${report.dataset_id}/${fmt === 'pdf' ? 'pdf-full' : fmt}`,
        {
          sections: report.sections,
          recommendations: report.recommendations,
        },
        { responseType: 'blob' }
      )
      const blob = new Blob([res.data], {
        type:
          fmt === 'pdf'
            ? 'application/pdf'
            : fmt === 'docx'
            ? 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            : 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `Analyticx_Report_${report.dataset_name.replace(' ', '_')}.${fmt}`
      link.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      alert(`Download failed: ${getErrorMessage(err)}`)
    }
  }

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center space-y-3">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-cyan-400 border-t-transparent" />
          <p className="text-sm text-slate-400">Loading Shared Executive Briefing...</p>
        </div>
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="glass max-w-xl mx-auto rounded-3xl p-8 text-center space-y-4 my-12">
        <div className="flex h-12 w-12 mx-auto items-center justify-center rounded-2xl bg-red-500/10 text-red-400">
          <AlertTriangle size={24} />
        </div>
        <h2 className="text-lg font-bold text-slate-100">Report Not Found or Expired</h2>
        <p className="text-xs text-slate-400">
          {error || 'This report link is invalid or may have been deleted.'}
        </p>
        <Link
          to="/"
          className="inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-4 py-2 text-xs font-semibold text-slate-950 hover:bg-cyan-300 transition"
        >
          Return to Analyticx Home
        </Link>
      </div>
    )
  }

  const rc = report.root_cause_data

  return (
    <div className="max-w-4xl mx-auto space-y-8 py-4">
      {/* Top Header Actions (Hidden in Print) */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4 print:hidden">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-cyan-400/20 text-cyan-300 font-bold">
            <Activity size={20} />
          </div>
          <div>
            <h1 className="text-base font-bold text-slate-100">Analyticx AI Shared Executive Briefing</h1>
            <p className="text-[11px] text-slate-400">Public decision support document</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleCopyLink}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/80 px-3 py-1.5 text-xs text-slate-200 hover:border-cyan-400 hover:text-cyan-200 transition"
          >
            {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
            {copied ? 'Link Copied!' : 'Copy Link'}
          </button>
          <button
            onClick={() => downloadFormat('pdf')}
            className="inline-flex items-center gap-1.5 rounded-xl bg-cyan-400 px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-cyan-300 transition shadow-sm"
          >
            <Download size={13} />
            PDF
          </button>
          <button
            onClick={() => downloadFormat('docx')}
            className="inline-flex items-center gap-1.5 rounded-xl border border-blue-500/40 bg-blue-500/10 px-3 py-1.5 text-xs font-semibold text-blue-300 hover:bg-blue-500/20 transition"
          >
            <FileText size={13} />
            Word (.docx)
          </button>
          <button
            onClick={() => downloadFormat('pptx')}
            className="inline-flex items-center gap-1.5 rounded-xl border border-purple-500/40 bg-purple-500/10 px-3 py-1.5 text-xs font-semibold text-purple-300 hover:bg-purple-500/20 transition"
          >
            <Download size={13} />
            PowerPoint (.pptx)
          </button>
          <button
            onClick={handlePrint}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:text-slate-100 transition"
            title="Print Document"
          >
            <Printer size={13} />
            Print
          </button>
        </div>
      </div>

      {/* Main Printable Document Card */}
      <div className="glass rounded-3xl p-8 sm:p-12 space-y-8 bg-slate-950/80 border border-slate-800 shadow-2xl print:bg-white print:text-black print:border-none print:shadow-none">
        {/* Document Header */}
        <div className="border-b border-slate-800 pb-6 print:border-gray-300 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-400 print:text-blue-600 font-bold">
              Analyticx AI · Executive Management Report
            </span>
            <span className="rounded-full bg-slate-900 border border-slate-700 px-2.5 py-0.5 text-[10px] text-slate-300 print:border-gray-400 print:text-black">
              Verified Analytics
            </span>
          </div>
          <h2 className="text-3xl font-extrabold tracking-tight text-slate-100 print:text-black">
            {report.title}
          </h2>
          <p className="text-xs text-slate-400 print:text-gray-600">
            Target Dataset: <strong className="text-slate-200 print:text-black">{report.dataset_name}</strong> · Generated on {new Date(report.generated_at).toLocaleString()}
          </p>
        </div>

        {/* Executive Summary */}
        {report.executive_summary && (
          <div className="rounded-2xl border border-cyan-500/30 bg-cyan-950/20 p-5 text-sm leading-relaxed text-cyan-100 print:bg-gray-100 print:border-gray-300 print:text-black">
            <p className="text-xs font-bold uppercase tracking-wider text-cyan-400 print:text-blue-800 mb-1">
              Executive Takeaway:
            </p>
            {report.executive_summary}
          </div>
        )}

        {/* Root-Cause Variance Decomposition (if present) */}
        {rc && (
          <div className="space-y-4">
            <h3 className="text-lg font-bold text-slate-100 print:text-black flex items-center gap-2">
              {rc.total_delta < 0 ? (
                <TrendingDown className="text-rose-400 print:text-red-600" size={20} />
              ) : (
                <TrendingUp className="text-emerald-400 print:text-green-600" size={20} />
              )}
              Root-Cause Variance Breakdown ({rc.metric_column.toUpperCase()})
            </h3>

            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 print:bg-gray-50 print:border-gray-300">
                <p className="text-[11px] text-slate-400 print:text-gray-500">Baseline Level</p>
                <p className="text-base font-bold text-slate-100 print:text-black">{rc.baseline_value.toLocaleString()}</p>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 print:bg-gray-50 print:border-gray-300">
                <p className="text-[11px] text-slate-400 print:text-gray-500">Comparison Level</p>
                <p className="text-base font-bold text-slate-100 print:text-black">{rc.comparison_value.toLocaleString()}</p>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 print:bg-gray-50 print:border-gray-300">
                <p className="text-[11px] text-slate-400 print:text-gray-500">Net Variance (Delta)</p>
                <p className={`text-base font-bold ${rc.total_delta < 0 ? 'text-rose-400 print:text-red-600' : 'text-emerald-400 print:text-green-600'}`}>
                  {rc.total_delta > 0 ? '+' : ''}{rc.total_delta.toLocaleString()} ({rc.percent_change}%)
                </p>
              </div>
            </div>

            {/* Waterfall Breakdown Steps */}
            {rc.waterfall_steps && rc.waterfall_steps.length > 0 && (
              <div className="space-y-2 pt-2">
                <p className="text-xs font-semibold text-slate-300 print:text-black">
                  Driver Decomposition by Dimension: <em>{rc.primary_driver_dimension}</em>
                </p>
                <div className="space-y-1.5">
                  {rc.waterfall_steps.map((step, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-2.5 rounded-lg border border-slate-800 bg-slate-900/40 text-xs print:bg-gray-50 print:border-gray-300"
                    >
                      <span className="text-slate-200 print:text-black font-medium">{step.name}</span>
                      <div className="flex items-center gap-3 font-mono">
                        {step.contribution_share !== undefined && (
                          <span className="text-[10px] text-slate-400 print:text-gray-600">
                            {step.contribution_share}% share
                          </span>
                        )}
                        <span className={step.value < 0 ? 'text-rose-400 print:text-red-600 font-bold' : 'text-emerald-400 print:text-green-600 font-bold'}>
                          {step.value > 0 && step.type === 'delta' ? '+' : ''}
                          {step.value.toLocaleString()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Detailed Report Sections & Data Tables */}
        {report.sections.map((sec, idx) => (
          <div key={idx} className="space-y-3">
            <h3 className="text-base font-bold text-slate-100 print:text-black border-b border-slate-800/80 pb-2 print:border-gray-300">
              {sec.title}
            </h3>
            {sec.text && <p className="text-xs text-slate-300 print:text-gray-700 leading-relaxed">{sec.text}</p>}

            {sec.rows && sec.rows.length > 0 && (
              <div className="overflow-x-auto rounded-xl border border-slate-800 print:border-gray-300">
                <table className="w-full text-left text-xs text-slate-200 print:text-black">
                  <thead className="bg-slate-900 text-slate-400 print:bg-gray-200 print:text-black">
                    <tr>
                      {Object.keys(sec.rows[0]).map((k) => (
                        <th key={k} className="p-2.5 font-bold">
                          {k}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 print:divide-gray-300">
                    {sec.rows.map((row, rIdx) => (
                      <tr key={rIdx} className="hover:bg-slate-900/30 print:hover:bg-transparent">
                        {Object.values(row).map((v, cIdx) => (
                          <td key={cIdx} className="p-2.5 font-mono">
                            {String(v ?? '')}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ))}

        {/* Strategic Recommendations */}
        {report.recommendations.length > 0 && (
          <div className="space-y-3 pt-4 border-t border-slate-800 print:border-gray-300">
            <h3 className="text-base font-bold text-slate-100 print:text-black flex items-center gap-2">
              <Lightbulb size={18} className="text-amber-400 print:text-amber-600" />
              Strategic Recommendations & Action Items
            </h3>
            <div className="space-y-2">
              {report.recommendations.map((rec, i) => (
                <div
                  key={i}
                  className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 text-xs text-amber-200 print:bg-gray-100 print:border-gray-300 print:text-black flex items-start gap-2.5"
                >
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-500/20 font-bold text-[10px] text-amber-300 print:text-black">
                    {i + 1}
                  </span>
                  <span className="leading-relaxed">{rec}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="pt-6 border-t border-slate-800/60 text-center text-[10px] text-slate-500 print:border-gray-300 print:text-gray-600">
          Analyticx AI Platform · Local-first Business Intelligence Engine · Grounded Verification
        </div>
      </div>
    </div>
  )
}
