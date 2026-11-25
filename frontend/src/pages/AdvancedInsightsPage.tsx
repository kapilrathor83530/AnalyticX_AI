import {
  AlertCircle,
  AlertTriangle,
  ArrowDownRight,
  ArrowLeft,
  ArrowUpRight,
  BarChart3,
  Calendar,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  Download,
  ExternalLink,
  FileSpreadsheet,
  FileText,
  Lightbulb,
  Play,
  Presentation,
  RefreshCw,
  Share2,
  Sliders,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Zap,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client'

interface RootCauseResult {
  metric_column: string
  primary_driver_dimension: string
  baseline_period: string
  comparison_period: string
  baseline_value: number
  comparison_value: number
  total_delta: number
  percent_change: number
  direction: string
  dimensions: Record<string, {
    dimension: string
    unique_segments: number
    top_detractors: {
      segment: string
      baseline_value: number
      comparison_value: number
      delta: number
      percent_change: number
      contribution_share: number
    }[]
    top_contributors: {
      segment: string
      baseline_value: number
      comparison_value: number
      delta: number
      percent_change: number
      contribution_share: number
    }[]
  }>
  waterfall_steps: {
    name: string
    value: number
    type: 'total' | 'delta'
    contribution_share?: number
  }[]
  recommendations: string[]
  executive_summary: string
}

interface ReportSchedule {
  id: string
  name: string
  frequency: string
  day: string
  time: string
  format: string
  active: boolean
  recipient_emails: string[]
  last_run: string | null
  next_run: string | null
}

export default function AdvancedInsightsPage() {
  const { id } = useParams()
  const datasetId = Number(id)

  const [columns, setColumns] = useState<string[]>([])
  const [metricColumn, setMetricColumn] = useState('')
  const [activeTab, setActiveTab] = useState<'root_cause' | 'anomalies' | 'reports' | 'automation'>('root_cause')

  // Root cause state
  const [rootCause, setRootCause] = useState<RootCauseResult | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState('')
  const [statusMessage, setStatusMessage] = useState('')

  // Anomaly detection state
  const [anomalyCol, setAnomalyCol] = useState('')
  const [anomalyThreshold, setAnomalyThreshold] = useState(3.0)
  const [anomalies, setAnomalies] = useState<Array<{ index: number; value: number; z_score?: number }>>([])
  const [scanningAnomalies, setScanningAnomalies] = useState(false)

  // Report sharing state
  const [shareUrl, setShareUrl] = useState('')
  const [copiedShare, setCopiedShare] = useState(false)
  const [generatingShare, setGeneratingShare] = useState(false)

  // Report schedules
  const [schedules, setSchedules] = useState<ReportSchedule[]>([])
  const [newScheduleName, setNewScheduleName] = useState('Weekly Performance Review')
  const [newScheduleFreq, setNewScheduleFreq] = useState('weekly')
  const [newScheduleEmail, setNewScheduleEmail] = useState('exec@analyticx.ai')

  useEffect(() => {
    if (!datasetId) return
    api
      .get<{ columns: string[] }>(`/datasets/${datasetId}/preview`, { params: { limit: 1 } })
      .then((res) => {
        setColumns(res.data.columns)
        const found = res.data.columns.find((c) =>
          /profit|revenue|sales|cost|amount|price|margin/i.test(c)
        )
        if (found) {
          setMetricColumn(found)
          setAnomalyCol(found)
        } else if (res.data.columns.length > 0) {
          setMetricColumn(res.data.columns[0])
          setAnomalyCol(res.data.columns[0])
        }
      })
      .catch((err) => setError(getErrorMessage(err)))

    loadSchedules()
  }, [datasetId])

  async function loadSchedules() {
    try {
      const res = await api.get<{ schedules: ReportSchedule[] }>(`/reports/dataset/${datasetId}/schedules`)
      setSchedules(res.data.schedules || [])
    } catch {
      // ignore
    }
  }

  async function runRootCause() {
    if (!metricColumn) return
    setAnalyzing(true)
    setError('')
    try {
      const res = await api.post<RootCauseResult>(`/analytics/${datasetId}/root-cause`, {
        metric_column: metricColumn,
      })
      setRootCause(res.data)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setAnalyzing(false)
    }
  }

  async function runAnomalyScan() {
    if (!anomalyCol) return
    setScanningAnomalies(true)
    setError('')
    try {
      const res = await api.post<{ anomalies: Array<{ index: number; value: number; z_score?: number }> }>(
        `/analytics/${datasetId}/anomalies`,
        { column: anomalyCol, threshold: anomalyThreshold }
      )
      setAnomalies(res.data.anomalies || [])
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setScanningAnomalies(false)
    }
  }

  async function handleDownloadPDF() {
    try {
      setStatusMessage('Compiling Executive PDF Report...')
      const res = await api.post(
        `/reports/dataset/${datasetId}/pdf-full`,
        {
          sections: [
            {
              title: 'Root Cause & Executive Variance Breakdown',
              rows: rootCause ? [
                { Metric: rootCause.metric_column, Delta: `${rootCause.total_delta.toLocaleString()}`, "Change %": `${rootCause.percent_change}%` },
                { PrimaryDriver: rootCause.primary_driver_dimension, Baseline: `${rootCause.baseline_value.toLocaleString()}`, Comparison: `${rootCause.comparison_value.toLocaleString()}` },
              ] : [],
            },
          ],
        },
        { responseType: 'blob' }
      )
      const blob = new Blob([res.data], { type: 'application/pdf' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `Analyticx_Executive_Report_Dataset_${datasetId}.pdf`
      link.click()
      URL.revokeObjectURL(url)
      setStatusMessage('Executive PDF Downloaded!')
      setTimeout(() => setStatusMessage(''), 3000)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function handleDownloadDOCX() {
    try {
      setStatusMessage('Building Executive Microsoft Word (.docx) Report...')
      const res = await api.post(
        `/reports/dataset/${datasetId}/docx`,
        {
          recommendations: rootCause?.recommendations,
          sections: [
            {
              title: 'Executive Variance Summary',
              rows: rootCause ? [
                { Metric: rootCause.metric_column, Delta: `${rootCause.total_delta.toLocaleString()}`, Direction: rootCause.direction },
                { Driver: rootCause.primary_driver_dimension, "Change %": `${rootCause.percent_change}%` },
              ] : [],
            },
          ],
        },
        { responseType: 'blob' }
      )
      const blob = new Blob([res.data], {
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `Analyticx_Executive_Report_Dataset_${datasetId}.docx`
      link.click()
      URL.revokeObjectURL(url)
      setStatusMessage('Microsoft Word (.docx) Downloaded!')
      setTimeout(() => setStatusMessage(''), 3000)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function handleDownloadPPTX() {
    try {
      setStatusMessage('Building Executive PowerPoint (.pptx) Deck...')
      const res = await api.post(
        `/reports/dataset/${datasetId}/pptx`,
        {
          recommendations: rootCause?.recommendations,
          sections: [
            {
              title: 'Executive Variance Summary',
              rows: rootCause ? [
                { Metric: rootCause.metric_column, Delta: `${rootCause.total_delta.toLocaleString()}`, Direction: rootCause.direction },
                { Driver: rootCause.primary_driver_dimension, "Change %": `${rootCause.percent_change}%` },
              ] : [],
            },
          ],
        },
        { responseType: 'blob' }
      )
      const blob = new Blob([res.data], {
        type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `Analyticx_Executive_Deck_Dataset_${datasetId}.pptx`
      link.click()
      URL.revokeObjectURL(url)
      setStatusMessage('PowerPoint Presentation (.pptx) Downloaded!')
      setTimeout(() => setStatusMessage(''), 3000)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function handleCreateShareLink() {
    setGeneratingShare(true)
    setError('')
    try {
      const res = await api.post<{ success: boolean; share_token: string; share_url: string }>(
        `/reports/dataset/${datasetId}/share`,
        {
          title: `Executive Intelligence Report (Dataset #${datasetId})`,
          executive_summary: rootCause?.executive_summary || 'Verified business analytics briefing with root-cause decomposition.',
          root_cause_data: rootCause,
          sections: [
            {
              title: 'Executive Variance Summary',
              rows: rootCause ? [
                { Metric: rootCause.metric_column, Delta: `${rootCause.total_delta.toLocaleString()}`, Direction: rootCause.direction },
                { Driver: rootCause.primary_driver_dimension, "Change %": `${rootCause.percent_change}%` },
              ] : [],
            },
          ],
          recommendations: rootCause?.recommendations || [
            'Audit top variance detractors and recalibrate operational pricing.',
            'Scale inventory and marketing in highest contributing growth regions.',
            'Establish automated recurring telemetry alerts for margin anomalies.',
          ],
        }
      )
      const fullUrl = `${window.location.origin}${res.data.share_url}`
      setShareUrl(fullUrl)
      setStatusMessage('Public Sharable Link Generated!')
      setTimeout(() => setStatusMessage(''), 3000)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setGeneratingShare(false)
    }
  }

  function handleCopyShare() {
    if (!shareUrl) return
    navigator.clipboard.writeText(shareUrl)
    setCopiedShare(true)
    setTimeout(() => setCopiedShare(false), 2000)
  }

  async function handleCreateSchedule(e: React.FormEvent) {
    e.preventDefault()
    try {
      await api.post(`/reports/dataset/${datasetId}/schedules`, {
        name: newScheduleName,
        frequency: newScheduleFreq,
        recipient_emails: [newScheduleEmail],
      })
      setStatusMessage('Automated Report Schedule Activated!')
      setTimeout(() => setStatusMessage(''), 3000)
      loadSchedules()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb */}
      <div className="flex items-center justify-between">
        <Link
          to={`/datasets/${datasetId}`}
          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-xs text-cyan-300 transition hover:border-cyan-500/50 hover:bg-slate-800"
        >
          <ArrowLeft size={14} />
          Back to Dataset Studio
        </Link>
        <span className="rounded-full border border-purple-500/30 bg-purple-500/10 px-2.5 py-0.5 text-xs font-semibold text-purple-300">
          Advanced Mode · Business Intelligence & Automation
        </span>
      </div>

      {/* Page Title */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-100 flex items-center gap-2.5">
          <Sparkles className="text-purple-400" size={26} />
          Executive Intelligence, Insights & Automation
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Decompose root causes behind business changes, detect metric anomalies, generate downloadable PDF/Word/PowerPoint reports, and share live briefs.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 pb-3">
        <button
          onClick={() => setActiveTab('root_cause')}
          className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-medium transition ${
            activeTab === 'root_cause'
              ? 'bg-purple-500/20 text-purple-200 border border-purple-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <TrendingDown size={14} className="text-purple-400" />
          Root-Cause & Driver Analysis
        </button>
        <button
          onClick={() => setActiveTab('anomalies')}
          className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-medium transition ${
            activeTab === 'anomalies'
              ? 'bg-purple-500/20 text-purple-200 border border-purple-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Zap size={14} className="text-amber-400" />
          Anomaly Detection
        </button>
        <button
          onClick={() => setActiveTab('reports')}
          className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-medium transition ${
            activeTab === 'reports'
              ? 'bg-purple-500/20 text-purple-200 border border-purple-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Presentation size={14} className="text-cyan-400" />
          Automated Reports (PDF, Word, PPTX & Share)
        </button>
        <button
          onClick={() => setActiveTab('automation')}
          className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-medium transition ${
            activeTab === 'automation'
              ? 'bg-purple-500/20 text-purple-200 border border-purple-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Clock size={14} className="text-emerald-400" />
          Scheduled Automation
        </button>
      </div>

      {/* Notification banner */}
      {statusMessage && (
        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-2.5 text-xs text-emerald-200 flex items-center gap-2">
          <CheckCircle2 size={15} className="text-emerald-400" />
          {statusMessage}
        </div>
      )}
      {error && (
        <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-2.5 text-xs text-red-200 flex items-center gap-2">
          <AlertTriangle size={15} className="text-red-400" />
          {error}
        </div>
      )}

      {/* TAB 1: ROOT-CAUSE ANALYSIS */}
      {activeTab === 'root_cause' && (
        <div className="space-y-6">
          <div className="glass rounded-3xl p-5 flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <label className="text-xs font-semibold text-slate-300">Target Metric:</label>
              <select
                value={metricColumn}
                onChange={(e) => setMetricColumn(e.target.value)}
                className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 focus:border-purple-400 focus:outline-none"
              >
                {columns.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
              <p className="text-xs text-slate-400">
                Calculates contribution share and decomposes detractors behind variance.
              </p>
            </div>

            <button
              onClick={runRootCause}
              disabled={analyzing || !metricColumn}
              className="inline-flex items-center gap-2 rounded-xl bg-purple-500 px-4 py-2 text-xs font-semibold text-white hover:bg-purple-400 disabled:opacity-50 transition shadow-md shadow-purple-950"
            >
              <Play size={13} className={analyzing ? 'animate-spin' : ''} />
              {analyzing ? 'Decomposing Drivers...' : 'Investigate Root Cause'}
            </button>
          </div>

          {rootCause ? (
            <div className="space-y-6">
              {/* Executive Summary Card */}
              <div className="glass rounded-3xl p-6 border-l-4 border-purple-500 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {rootCause.total_delta < 0 ? (
                      <TrendingDown size={22} className="text-rose-400" />
                    ) : (
                      <TrendingUp size={22} className="text-emerald-400" />
                    )}
                    <h2 className="text-lg font-bold text-slate-100">
                      {rootCause.metric_column.toUpperCase()} {rootCause.direction.toUpperCase()} BY{' '}
                      {Math.abs(rootCause.total_delta).toLocaleString()} ({rootCause.percent_change}%)
                    </h2>
                  </div>
                  <span className="text-xs text-slate-400">
                    Primary Driver: <strong className="text-purple-300">{rootCause.primary_driver_dimension}</strong>
                  </span>
                </div>

                <p className="text-sm leading-relaxed text-slate-300">{rootCause.executive_summary}</p>

                <div className="grid gap-3 pt-2 sm:grid-cols-3">
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-3">
                    <p className="text-[11px] text-slate-400">{rootCause.baseline_period}</p>
                    <p className="text-base font-bold text-slate-100">{rootCause.baseline_value.toLocaleString()}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-3">
                    <p className="text-[11px] text-slate-400">{rootCause.comparison_period}</p>
                    <p className="text-base font-bold text-slate-100">{rootCause.comparison_value.toLocaleString()}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-3">
                    <p className="text-[11px] text-slate-400">Net Variance (Delta)</p>
                    <p
                      className={`text-base font-bold ${
                        rootCause.total_delta < 0 ? 'text-rose-400' : 'text-emerald-400'
                      }`}
                    >
                      {rootCause.total_delta > 0 ? '+' : ''}
                      {rootCause.total_delta.toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>

              {/* Waterfall & Recommendations */}
              <div className="grid gap-6 lg:grid-cols-2">
                <div className="glass rounded-3xl p-6 space-y-4">
                  <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                    <BarChart3 size={16} className="text-purple-400" />
                    Variance Waterfall Decomposition ({rootCause.primary_driver_dimension})
                  </h3>
                  <div className="space-y-2.5 pt-1">
                    {rootCause.waterfall_steps.map((step, idx) => (
                      <div
                        key={idx}
                        className={`flex items-center justify-between p-3 rounded-xl border text-xs ${
                          step.type === 'total'
                            ? 'border-purple-500/40 bg-purple-950/20 font-semibold text-purple-200'
                            : step.value < 0
                            ? 'border-rose-500/30 bg-rose-500/10 text-rose-300'
                            : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          {step.type === 'delta' && step.value < 0 && <ArrowDownRight size={14} />}
                          {step.type === 'delta' && step.value > 0 && <ArrowUpRight size={14} />}
                          <span>{step.name}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          {step.contribution_share !== undefined && (
                            <span className="text-[10px] text-slate-400">
                              {step.contribution_share}% share
                            </span>
                          )}
                          <span className="font-mono font-semibold">
                            {step.value > 0 && step.type === 'delta' ? '+' : ''}
                            {step.value.toLocaleString()}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="glass rounded-3xl p-6 space-y-4">
                  <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                    <Lightbulb size={16} className="text-amber-400" />
                    Data-Backed Strategic Recommendations
                  </h3>
                  <div className="space-y-3">
                    {rootCause.recommendations.map((rec, i) => (
                      <div
                        key={i}
                        className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-3.5 text-xs leading-relaxed text-amber-200 flex items-start gap-2.5"
                      >
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-500/20 font-bold text-[10px] text-amber-300">
                          {i + 1}
                        </span>
                        <span>{rec}</span>
                      </div>
                    ))}
                  </div>

                  {rootCause.primary_driver_dimension &&
                    rootCause.dimensions[rootCause.primary_driver_dimension]?.top_detractors.length > 0 && (
                      <div className="pt-2">
                        <p className="text-xs font-semibold text-rose-300 mb-2">Top Detractor Segments:</p>
                        <div className="space-y-1.5">
                          {rootCause.dimensions[rootCause.primary_driver_dimension].top_detractors.map((det) => (
                            <div
                              key={det.segment}
                              className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/60 p-2.5 text-xs"
                            >
                              <span className="text-slate-300 font-medium">{det.segment}</span>
                              <div className="flex items-center gap-3 text-rose-400 font-mono">
                                <span>{det.delta.toLocaleString()}</span>
                                <span className="text-[10px] text-slate-500">({det.contribution_share}%)</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                </div>
              </div>
            </div>
          ) : (
            <div className="glass rounded-3xl p-12 text-center space-y-3">
              <div className="flex h-12 w-12 mx-auto items-center justify-center rounded-2xl bg-purple-500/10 text-purple-400">
                <TrendingDown size={24} />
              </div>
              <h3 className="text-base font-semibold text-slate-200">No Root-Cause Analysis Run Yet</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Select your target metric above (e.g. Profit, Sales, Revenue) and click <strong>"Investigate Root Cause"</strong>.
              </p>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: ANOMALY DETECTION */}
      {activeTab === 'anomalies' && (
        <div className="space-y-6">
          <div className="glass rounded-3xl p-5 flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <label className="text-xs font-semibold text-slate-300">Analyze Column:</label>
              <select
                value={anomalyCol}
                onChange={(e) => setAnomalyCol(e.target.value)}
                className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 focus:border-purple-400 focus:outline-none"
              >
                {columns.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>

              <span className="text-xs text-slate-400">Sensitivity Threshold (Z-score):</span>
              <select
                value={anomalyThreshold}
                onChange={(e) => setAnomalyThreshold(Number(e.target.value))}
                className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 focus:border-purple-400 focus:outline-none"
              >
                <option value={2.0}>Strict (2.0 Std Dev)</option>
                <option value={2.5}>Moderate (2.5 Std Dev)</option>
                <option value={3.0}>Standard (3.0 Std Dev)</option>
                <option value={3.5}>Loose (3.5 Std Dev)</option>
              </select>
            </div>

            <button
              onClick={runAnomalyScan}
              disabled={scanningAnomalies || !anomalyCol}
              className="inline-flex items-center gap-2 rounded-xl bg-amber-400 px-4 py-2 text-xs font-semibold text-slate-950 hover:bg-amber-300 disabled:opacity-50 transition shadow-md shadow-amber-950"
            >
              <Zap size={13} className={scanningAnomalies ? 'animate-spin' : ''} />
              {scanningAnomalies ? 'Scanning Anomaly Spikes...' : 'Scan Anomalies'}
            </button>
          </div>

          {anomalies.length > 0 ? (
            <div className="glass rounded-3xl p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                  <AlertCircle size={18} className="text-rose-400" />
                  Detected Statistical Anomalies in '{anomalyCol}' ({anomalies.length} outliers)
                </h3>
              </div>

              <div className="max-h-80 overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900/40">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="sticky top-0 bg-slate-900 text-[11px] font-semibold uppercase tracking-wider text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="p-3">Record Row Index</th>
                      <th className="p-3">Anomalous Value</th>
                      <th className="p-3">Z-Score Deviation</th>
                      <th className="p-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {anomalies.map((anom, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/30 transition">
                        <td className="p-3 font-mono text-slate-400">Row #{anom.index}</td>
                        <td className="p-3 font-mono font-bold text-rose-300">{anom.value?.toLocaleString() ?? '—'}</td>
                        <td className="p-3 font-mono text-amber-300">{anom.z_score !== undefined ? `${round(anom.z_score, 2)} σ` : 'Outlier'}</td>
                        <td className="p-3">
                          <span className="rounded-full bg-rose-500/10 border border-rose-500/30 px-2 py-0.5 text-[10px] text-rose-300 font-semibold">
                            Critical Outlier
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="glass rounded-3xl p-12 text-center space-y-3">
              <div className="flex h-12 w-12 mx-auto items-center justify-center rounded-2xl bg-amber-500/10 text-amber-400">
                <Zap size={24} />
              </div>
              <h3 className="text-base font-semibold text-slate-200">No Outliers Flagged Yet</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Select a numerical business field (e.g. Sales, Profit, Units, Discount) and click <strong>"Scan Anomalies"</strong> to detect extreme irregularities.
              </p>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: AUTOMATED REPORTS (PDF, WORD, PPTX & SHARE) */}
      {activeTab === 'reports' && (
        <div className="space-y-6">
          {/* Share Link Banner */}
          <div className="glass rounded-3xl p-6 border border-cyan-500/30 bg-gradient-to-r from-cyan-950/30 to-purple-950/30 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-400/20 text-cyan-300">
                  <Share2 size={20} />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-100">Live Executive Web Briefing & Share Link</h3>
                  <p className="text-xs text-slate-400">
                    Publish an executive report URL that can be viewed and printed by stakeholders without login credentials.
                  </p>
                </div>
              </div>

              <button
                onClick={handleCreateShareLink}
                disabled={generatingShare}
                className="inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-4 py-2.5 text-xs font-semibold text-slate-950 hover:bg-cyan-300 transition shadow-md shadow-cyan-950"
              >
                <Share2 size={14} className={generatingShare ? 'animate-spin' : ''} />
                {generatingShare ? 'Generating...' : 'Generate Sharable Link'}
              </button>
            </div>

            {shareUrl && (
              <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800">
                <input
                  type="text"
                  readOnly
                  value={shareUrl}
                  className="flex-1 rounded-xl border border-slate-700 bg-slate-900/90 px-3.5 py-2 text-xs font-mono text-cyan-200 outline-none"
                />
                <button
                  onClick={handleCopyShare}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-slate-800 border border-slate-700 px-3.5 py-2 text-xs font-semibold text-slate-200 hover:text-cyan-300 hover:border-cyan-400 transition"
                >
                  {copiedShare ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
                  {copiedShare ? 'Copied!' : 'Copy Link'}
                </button>
                <a
                  href={shareUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-xl border border-cyan-500/40 bg-cyan-500/10 px-3.5 py-2 text-xs font-semibold text-cyan-300 hover:bg-cyan-500/20 transition"
                >
                  <ExternalLink size={13} />
                  Open Briefing
                </a>
              </div>
            )}
          </div>

          {/* Download Cards Grid */}
          <div className="grid gap-6 md:grid-cols-3">
            {/* Card 1: PDF */}
            <div className="glass rounded-3xl p-6 space-y-4 border border-slate-800 hover:border-cyan-500/40 transition flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-400/10 text-cyan-400">
                  <FileText size={20} />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-slate-100">Executive PDF Report</h3>
                  <p className="text-xs text-slate-400 mt-1">
                    Presentation-ready PDF with data profiles, root-cause tables, and strict numerical verification notes.
                  </p>
                </div>
              </div>
              <button
                onClick={handleDownloadPDF}
                className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-400 py-2.5 text-xs font-semibold text-slate-950 hover:bg-cyan-300 transition shadow-md shadow-cyan-950"
              >
                <Download size={14} />
                Download PDF
              </button>
            </div>

            {/* Card 2: Microsoft Word (.docx) */}
            <div className="glass rounded-3xl p-6 space-y-4 border border-slate-800 hover:border-blue-500/40 transition flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
                  <FileSpreadsheet size={20} />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-slate-100">Microsoft Word (.docx)</h3>
                  <p className="text-xs text-slate-400 mt-1">
                    Editable Word document with styled executive tables, section titles, and numbered action recommendations.
                  </p>
                </div>
              </div>
              <button
                onClick={handleDownloadDOCX}
                className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-blue-500 py-2.5 text-xs font-semibold text-white hover:bg-blue-400 transition shadow-md shadow-blue-950"
              >
                <Download size={14} />
                Download Word (.docx)
              </button>
            </div>

            {/* Card 3: PowerPoint (.pptx) */}
            <div className="glass rounded-3xl p-6 space-y-4 border border-slate-800 hover:border-purple-500/40 transition flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-500/10 text-purple-400">
                  <Presentation size={20} />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-slate-100">PowerPoint Deck (.pptx)</h3>
                  <p className="text-xs text-slate-400 mt-1">
                    Presentation slides covering Summary, Drivers, Findings, and Strategic Next Steps.
                  </p>
                </div>
              </div>
              <button
                onClick={handleDownloadPPTX}
                className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-purple-500 py-2.5 text-xs font-semibold text-white hover:bg-purple-400 transition shadow-md shadow-purple-950"
              >
                <Download size={14} />
                Download PowerPoint (.pptx)
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: REPORT AUTOMATION & SCHEDULER */}
      {activeTab === 'automation' && (
        <div className="space-y-6">
          <div className="glass rounded-3xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
                <Calendar size={18} className="text-emerald-400" />
                Configured Recurring Report Automations
              </h3>
              <span className="text-xs text-slate-400">{schedules.length} active schedule(s)</span>
            </div>

            <div className="space-y-3">
              {schedules.map((sched) => (
                <div
                  key={sched.id}
                  className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-4"
                >
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-slate-200">{sched.name}</p>
                    <p className="text-xs text-slate-400">
                      Frequency: <strong className="text-emerald-400 capitalize">{sched.frequency}</strong> ({sched.day || 'Daily'} at {sched.time || '08:00 UTC'})
                    </p>
                    <p className="text-[11px] text-slate-500">Recipients: {sched.recipient_emails.join(', ')}</p>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs text-emerald-300">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      Active Cron Trigger
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="glass rounded-3xl p-6 space-y-4">
            <h3 className="text-sm font-semibold text-slate-200">Add Automated Recurring Report</h3>
            <form onSubmit={handleCreateSchedule} className="grid gap-4 sm:grid-cols-3">
              <div>
                <label className="mb-1 block text-xs text-slate-400">Report Name</label>
                <input
                  type="text"
                  value={newScheduleName}
                  onChange={(e) => setNewScheduleName(e.target.value)}
                  className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-emerald-400 focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="mb-1 block text-xs text-slate-400">Recurrence Frequency</label>
                <select
                  value={newScheduleFreq}
                  onChange={(e) => setNewScheduleFreq(e.target.value)}
                  className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-emerald-400 focus:outline-none"
                >
                  <option value="daily">Daily Morning Digest</option>
                  <option value="weekly">Weekly Executive Review (Mondays)</option>
                  <option value="monthly">Monthly Board Deck</option>
                </select>
              </div>

              <div>
                <label className="mb-1 block text-xs text-slate-400">Executive Email</label>
                <input
                  type="email"
                  value={newScheduleEmail}
                  onChange={(e) => setNewScheduleEmail(e.target.value)}
                  className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-emerald-400 focus:outline-none"
                  required
                />
              </div>

              <div className="sm:col-span-3 flex justify-end">
                <button
                  type="submit"
                  className="rounded-xl bg-emerald-400 px-4 py-2 text-xs font-semibold text-slate-950 hover:bg-emerald-300 transition shadow-md shadow-emerald-950"
                >
                  Save & Enable Schedule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

function round(val: number, decimals: number) {
  return Number(Math.round(Number(val + 'e' + decimals)) + 'e-' + decimals)
}
