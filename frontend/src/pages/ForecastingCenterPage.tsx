import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Award,
  BarChart3,
  Brain,
  CheckCircle2,
  Clock,
  Compass,
  Copy,
  Database,
  Download,
  ExternalLink,
  Eye,
  FileSpreadsheet,
  FileText,
  Filter,
  HelpCircle,
  Layers,
  LayoutDashboard,
  Lightbulb,
  MessageSquare,
  Play,
  Presentation,
  RefreshCw,
  Send,
  Share2,
  ShieldAlert,
  Sliders,
  Sparkles,
  TrendingDown,
  TrendingUp,
  X,
  Zap,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import Plot from 'react-plotly.js'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client'
import { forecastService } from '../services/forecastService'
import { reportService } from '../services/reportService'
import type {
  CandidateModelInfo,
  ForecastRun,
  ForecastScenario,
  TimeSeriesReadiness,
} from '../types/forecast'

interface DatasetOption {
  id: number
  name: string
  row_count: number
  column_count: number
}

interface ChatMessage {
  id: string
  sender: 'user' | 'ai'
  text: string
  timestamp: string
}

export default function ForecastingCenterPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const datasetId = Number(id) || 1

  // Datasets & Readiness State
  const [datasets, setDatasets] = useState<DatasetOption[]>([])
  const [readiness, setReadiness] = useState<TimeSeriesReadiness | null>(null)
  const [columns, setColumns] = useState<string[]>([])

  // Form Configuration State
  const [dateColumn, setDateColumn] = useState('')
  const [targetColumn, setTargetColumn] = useState('')
  const [groupDimension, setGroupDimension] = useState('')
  const [groupValue, setGroupValue] = useState('')
  const [horizon, setHorizon] = useState(12)
  const [frequency, setFrequency] = useState('M')
  const [modelType, setModelType] = useState('auto')
  const [fillStrategy, setFillStrategy] = useState<'interpolate' | 'ffill' | 'zero' | 'mean'>('interpolate')
  const [handleOutliers, setHandleOutliers] = useState(true)
  const [showAdvanced, setShowAdvanced] = useState(false)

  // Custom What-If Scenario Inputs
  const [growthRatePct, setGrowthRatePct] = useState(0)
  const [priceChangePct, setPriceChangePct] = useState(0)
  const [priceElasticity, setPriceElasticity] = useState(-1.2)
  const [marketingBudgetPct, setMarketingBudgetPct] = useState(0)
  const [marketingElasticity, setMarketingElasticity] = useState(0.35)

  // Execution & Results State
  const [loading, setLoading] = useState(false)
  const [inspecting, setInspecting] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [activeRun, setActiveRun] = useState<ForecastRun | null>(null)
  const [pastRuns, setPastRuns] = useState<ForecastRun[]>([])
  const [activeChartTab, setActiveChartTab] = useState<'forecast' | 'backtest' | 'scenarios'>('forecast')

  // Grounded AI Chat State
  const [chatOpen, setChatOpen] = useState(false)
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: 'init',
      sender: 'ai',
      text: "Welcome to Forecasting Lab. I can explain projected trajectories, uncertainty confidence intervals, holdout backtest scores, and what-if assumptions.",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ])

  // 1. Load dataset options and inspect readiness
  useEffect(() => {
    api
      .get<DatasetOption[]>('/datasets')
      .then((res) => {
        setDatasets(res.data)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!datasetId) return

    async function inspectAndLoad() {
      setInspecting(true)
      setError('')
      try {
        const [readinessData, existingRuns, preview] = await Promise.all([
          forecastService.inspect(datasetId),
          forecastService.list(datasetId),
          api.get<{ columns: string[] }>(`/datasets/${datasetId}/preview`, { params: { limit: 1 } }),
        ])

        setReadiness(readinessData)
        setPastRuns(existingRuns)
        setColumns(preview.data.columns)

        if (existingRuns.length > 0) {
          setActiveRun(existingRuns[0])
          setDateColumn(existingRuns[0].date_column)
          setTargetColumn(existingRuns[0].target_column)
          setHorizon(existingRuns[0].horizon)
          setFrequency(existingRuns[0].frequency.startsWith('M') ? 'M' : existingRuns[0].frequency)
        } else {
          // Pre-populate sensible defaults from readiness
          if (readinessData.recommended_date_column) {
            setDateColumn(readinessData.recommended_date_column)
          }
          if (readinessData.recommended_target_column) {
            setTargetColumn(readinessData.recommended_target_column)
          }
          if (readinessData.recommended_frequency) {
            const rf = readinessData.recommended_frequency
            setFrequency(rf.startsWith('M') ? 'M' : rf.startsWith('Q') ? 'Q' : rf.startsWith('W') ? 'W' : 'D')
          }
        }
      } catch (err) {
        setError(getErrorMessage(err))
      } finally {
        setInspecting(false)
      }
    }

    inspectAndLoad()
  }, [datasetId])

  // 2. Train and evaluate forecast
  const handleTrainForecast = async () => {
    if (!dateColumn || !targetColumn) {
      setError('Please select both a date column and a target metric to forecast.')
      return
    }

    setLoading(true)
    setError('')
    setSuccessMessage('')

    try {
      const run = await forecastService.train({
        dataset_id: datasetId,
        date_column: dateColumn,
        target_column: targetColumn,
        horizon: Number(horizon),
        frequency: frequency,
        model_type: modelType === 'auto' ? undefined : modelType,
        group_dimension: groupDimension || undefined,
        group_value: groupValue || undefined,
        fill_strategy: fillStrategy,
        handle_outliers: handleOutliers,
        custom_assumptions: {
          growth_rate_pct: Number(growthRatePct),
          price_change_pct: Number(priceChangePct),
          price_elasticity: Number(priceElasticity),
          marketing_budget_pct: Number(marketingBudgetPct),
          marketing_elasticity: Number(marketingElasticity),
        },
      })

      setActiveRun(run)
      setPastRuns((prev) => [run, ...prev])
      setSuccessMessage(`Forecast completed successfully! Selected champion model: ${run.model_type.toUpperCase()}.`)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  // 3. Pin to Dashboard
  const handlePinToDashboard = async () => {
    if (!activeRun) return
    try {
      const res = await forecastService.pinToDashboard(activeRun.id)
      setSuccessMessage(`Forecast chart pinned to Dashboard #${res.dashboard_id}!`)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  // 4. Export CSV & Reports
  const [downloadMenuOpen, setDownloadMenuOpen] = useState(false)

  const handleDownloadPDF = async () => {
    if (!activeRun) return
    setDownloadMenuOpen(false)
    try {
      await reportService.downloadDirect(
        `/reports/forecast/${datasetId}/download?format=pdf&run_id=${activeRun.id}`,
        `Analyticx_Forecast_${activeRun.target_column}_${activeRun.horizon}h.pdf`
      )
      setSuccessMessage('Forecast executive PDF report downloaded successfully.')
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const handleDownloadXLSX = async () => {
    if (!activeRun) return
    setDownloadMenuOpen(false)
    try {
      await reportService.downloadDirect(
        `/reports/forecast/${datasetId}/download?format=xlsx&run_id=${activeRun.id}`,
        `Analyticx_Forecast_Evaluation_${activeRun.target_column}.xlsx`
      )
      setSuccessMessage('Forecast evaluation Excel workbook downloaded successfully.')
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const handleDownloadPackage = async () => {
    setDownloadMenuOpen(false)
    try {
      await reportService.exportPackage({
        dataset_id: datasetId,
        selected_categories: ['forecast', 'statistical'],
      })
      setSuccessMessage('Forecast Project Package (ZIP) downloaded.')
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const handleExportCSV = () => {
    setDownloadMenuOpen(false)
    if (!activeRun) return
    const rows = [
      ['Date', 'Type', 'Value', 'Lower_80', 'Upper_80', 'Lower_95', 'Upper_95'],
      ...(activeRun.predictions || []).map((p) => [
        p.date.slice(0, 10),
        'Forecast',
        p.value,
        p.lower_80 ?? '',
        p.upper_80 ?? '',
        p.lower_95 ?? '',
        p.upper_95 ?? '',
      ]),
    ]
    const csvContent = 'data:text/csv;charset=utf-8,' + rows.map((e) => e.join(',')).join('\n')
    const encodedUri = encodeURI(csvContent)
    const link = document.createElement('a')
    link.setAttribute('href', encodedUri)
    link.setAttribute('download', `Forecast_${activeRun.target_column}_${activeRun.horizon}h.csv`)
    document.body.appendChild(link)
    link.click()
    link.remove()
  }

  // 5. Send Chat Query
  const handleSendChat = async (presetText?: string) => {
    const q = (presetText || chatInput).trim()
    if (!q || !activeRun || chatLoading) return

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: q,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }
    setChatMessages((prev) => [...prev, userMsg])
    setChatInput('')
    setChatLoading(true)

    try {
      const res = await forecastService.chat(activeRun.id, q)
      const aiMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: res.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }
      setChatMessages((prev) => [...prev, aiMsg])
    } catch (err) {
      const errReply: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: `Error analyzing forecast: ${getErrorMessage(err)}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }
      setChatMessages((prev) => [...prev, errReply])
    } finally {
      setChatLoading(false)
    }
  }

  // Historical dates & values for plotting
  const historyDates = useMemo(() => {
    return (activeRun?.predictions ? [] : [])
  }, [activeRun])

  return (
    <div className="space-y-6 pb-16">
      {/* 1. Header Bar with Dataset Switcher & Status Badges */}
      <div className="glass rounded-3xl p-6 border border-slate-800 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-500/20 to-purple-500/20 text-cyan-300 border border-cyan-500/30">
              <TrendingUp size={24} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400">
                  Forecasting Lab
                </span>
                <span className="text-slate-500">•</span>
                <span className="text-xs text-slate-400">Chronological Backtesting & Predictive Uncertainty</span>
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-100 flex items-center gap-3">
                Advanced AI Forecasting
              </h1>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Dataset Selector */}
            <div className="flex items-center gap-2 rounded-2xl border border-slate-800 bg-slate-900/80 px-3 py-1.5">
              <Database size={14} className="text-cyan-400" />
              <select
                value={datasetId}
                onChange={(e) => navigate(`/forecasting/${e.target.value}`)}
                className="bg-transparent text-xs font-semibold text-slate-200 focus:outline-none cursor-pointer"
              >
                {datasets.map((d) => (
                  <option key={d.id} value={d.id} className="bg-slate-900 text-slate-200">
                    {d.name} ({d.row_count} rows)
                  </option>
                ))}
              </select>
            </div>

            {activeRun && (
              <>
                <button
                  onClick={handlePinToDashboard}
                  className="inline-flex items-center gap-2 rounded-2xl border border-cyan-500/30 bg-cyan-500/10 px-3.5 py-2 text-xs font-semibold text-cyan-200 hover:bg-cyan-500/20 transition"
                  title="Pin forecast chart to project dashboard"
                >
                  <LayoutDashboard size={14} />
                  Pin to Dashboard
                </button>

                <div className="relative">
                  <button
                    onClick={() => setDownloadMenuOpen(!downloadMenuOpen)}
                    className="inline-flex items-center gap-2 rounded-2xl border border-slate-700 bg-slate-800/80 px-3.5 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition"
                    title="Download forecast reports and projections"
                  >
                    <Download size={14} />
                    Download Report
                  </button>

                  {downloadMenuOpen && (
                    <div className="absolute right-0 top-full mt-2 z-50 w-64 rounded-2xl border border-slate-700 bg-slate-900/95 p-2 shadow-2xl backdrop-blur-xl space-y-1">
                      <button
                        onClick={handleDownloadPDF}
                        className="w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-slate-200 hover:bg-slate-800 transition"
                      >
                        <FileText size={14} className="text-red-400" />
                        <div>
                          <p className="font-semibold">Executive PDF Report</p>
                          <p className="text-[10px] text-slate-400">Formatted brief with confidence intervals</p>
                        </div>
                      </button>

                      <button
                        onClick={handleDownloadXLSX}
                        className="w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-slate-200 hover:bg-slate-800 transition"
                      >
                        <FileSpreadsheet size={14} className="text-emerald-400" />
                        <div>
                          <p className="font-semibold">Model Evaluation (.xlsx)</p>
                          <p className="text-[10px] text-slate-400">Multi-sheet predictions and holdout curves</p>
                        </div>
                      </button>

                      <button
                        onClick={handleExportCSV}
                        className="w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-slate-200 hover:bg-slate-800 transition"
                      >
                        <Download size={14} className="text-cyan-400" />
                        <div>
                          <p className="font-semibold">Forecast Values (.csv)</p>
                          <p className="text-[10px] text-slate-400">Values with 80% and 95% bounds</p>
                        </div>
                      </button>

                      <button
                        onClick={handleDownloadPackage}
                        className="w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-slate-200 hover:bg-slate-800 transition border-t border-slate-800/80 mt-1 pt-1.5"
                      >
                        <Zap size={14} className="text-indigo-400" />
                        <div>
                          <p className="font-semibold">Complete Project Package (ZIP)</p>
                          <p className="text-[10px] text-slate-400">Bundles all forecasting and stats files</p>
                        </div>
                      </button>
                    </div>
                  )}
                </div>
              </>
            )}

            <button
              onClick={() => setChatOpen(!chatOpen)}
              className={`inline-flex items-center gap-2 rounded-2xl px-3.5 py-2 text-xs font-semibold transition ${
                chatOpen
                  ? 'bg-purple-500 text-white shadow-md shadow-purple-950'
                  : 'border border-purple-500/30 bg-purple-500/10 text-purple-200 hover:bg-purple-500/20'
              }`}
            >
              <MessageSquare size={14} />
              Forecasting Copilot
            </button>
          </div>
        </div>

        {/* Readiness Inspection Banner */}
        {readiness && (
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-800/60 text-xs">
            <div className="flex items-center gap-2">
              <span
                className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase border ${
                  readiness.is_ready
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                    : 'border-amber-500/30 bg-amber-500/10 text-amber-300'
                }`}
              >
                {readiness.is_ready ? 'Time-Series Ready' : 'Data Adaptation Notice'}
              </span>
              <span className="text-slate-400">{readiness.reason}</span>
            </div>

            {readiness.date_candidates.length > 0 && (
              <span className="text-slate-500 text-[11px]">
                Detected Time Column: <strong>{readiness.date_candidates[0].column}</strong> ({readiness.date_candidates[0].min_date} to {readiness.date_candidates[0].max_date})
              </span>
            )}
          </div>
        )}
      </div>

      {/* Notifications */}
      {error && (
        <div className="rounded-2xl border border-red-500/40 bg-red-500/10 p-4 text-xs text-red-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle size={16} className="text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError('')} className="text-slate-400 hover:text-slate-200">
            <X size={14} />
          </button>
        </div>
      )}

      {successMessage && (
        <div className="rounded-2xl border border-emerald-500/40 bg-emerald-500/10 p-4 text-xs text-emerald-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
            <span>{successMessage}</span>
          </div>
          <button onClick={() => setSuccessMessage('')} className="text-slate-400 hover:text-slate-200">
            <X size={14} />
          </button>
        </div>
      )}

      {/* 2. Configuration Panel */}
      <div className="glass rounded-3xl p-6 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
            <Sliders size={14} className="text-cyan-400" />
            Forecast Parameters & Model Strategy
          </h2>
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 transition"
          >
            {showAdvanced ? 'Hide Advanced Options' : 'Show Advanced Preprocessing & Scenarios'}
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
          {/* Target Metric */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-slate-400">Target Metric:</label>
            <select
              value={targetColumn}
              onChange={(e) => setTargetColumn(e.target.value)}
              className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-400"
            >
              <option value="">Select Metric</option>
              {columns.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          {/* Date Column */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-slate-400">Date/Time Column:</label>
            <select
              value={dateColumn}
              onChange={(e) => setDateColumn(e.target.value)}
              className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-400"
            >
              <option value="">Select Date Column</option>
              {columns.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          {/* Horizon */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-slate-400">Forecast Horizon:</label>
            <select
              value={horizon}
              onChange={(e) => setHorizon(Number(e.target.value))}
              className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-400"
            >
              <option value={7}>7 Periods</option>
              <option value={14}>14 Periods</option>
              <option value={30}>30 Periods</option>
              <option value={60}>60 Periods</option>
              <option value={90}>90 Periods</option>
              <option value={6}>6 Periods (e.g. 6 mos)</option>
              <option value={12}>12 Periods (1 Year)</option>
              <option value={24}>24 Periods (2 Years)</option>
            </select>
          </div>

          {/* Frequency */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-slate-400">Frequency:</label>
            <select
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
              className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-400"
            >
              <option value="D">Daily (D)</option>
              <option value="W">Weekly (W)</option>
              <option value="M">Monthly (M)</option>
              <option value="Q">Quarterly (Q)</option>
            </select>
          </div>

          {/* Model Selection */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-slate-400">Model Selection:</label>
            <select
              value={modelType}
              onChange={(e) => setModelType(e.target.value)}
              className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-400"
            >
              <option value="auto">Auto Champion Selection</option>
              <option value="exp_smoothing">Holt-Winters (ETS)</option>
              <option value="arima">ARIMA (p,d,q)</option>
              <option value="random_forest">Random Forest ML</option>
              <option value="linear">Linear Trend</option>
              <option value="seasonal_naive">Seasonal Naive</option>
              <option value="moving_average">Moving Average</option>
              <option value="naive">Naive Baseline</option>
            </select>
          </div>

          {/* Train Button */}
          <div className="flex items-end">
            <button
              onClick={handleTrainForecast}
              disabled={loading || !dateColumn || !targetColumn}
              className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-400 py-2.5 text-xs font-bold text-slate-950 hover:bg-cyan-300 transition shadow-md shadow-cyan-950 disabled:opacity-50"
            >
              <Play size={13} className={loading ? 'animate-spin' : ''} />
              {loading ? 'Evaluating Models...' : 'Train & Evaluate'}
            </button>
          </div>
        </div>

        {/* Collapsible Advanced Options: Preprocessing & What-If Assumptions */}
        {showAdvanced && (
          <div className="pt-4 border-t border-slate-800/80 space-y-4">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
              Data Preprocessing & Scenario Assumptions
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-400">Missing Intervals Imputation:</label>
                <select
                  value={fillStrategy}
                  onChange={(e) => setFillStrategy(e.target.value as any)}
                  className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 focus:outline-none"
                >
                  <option value="interpolate">Linear Interpolation (Recommended)</option>
                  <option value="ffill">Forward Fill</option>
                  <option value="zero">Zero Imputation</option>
                  <option value="mean">Historical Mean</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-400">Outlier Treatment:</label>
                <div className="flex items-center gap-2 pt-1.5">
                  <input
                    type="checkbox"
                    id="outlier_cb"
                    checked={handleOutliers}
                    onChange={(e) => setHandleOutliers(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-900 text-cyan-400"
                  />
                  <label htmlFor="outlier_cb" className="text-xs text-slate-300">
                    Apply Tukey IQR Winsorization (Caps extreme spikes)
                  </label>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-400">Segment Dimension (Optional):</label>
                <select
                  value={groupDimension}
                  onChange={(e) => setGroupDimension(e.target.value)}
                  className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 focus:outline-none"
                >
                  <option value="">None (Total Dataset)</option>
                  {readiness?.group_candidates?.map((g) => (
                    <option key={g.column} value={g.column}>{g.column}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Scenario Adjustment Sliders */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-purple-300 flex items-center gap-1.5">
                  <Sliders size={13} />
                  What-If Sensitivity Assumptions:
                </span>
                <span className="text-[11px] text-slate-400">Simulates macro changes on forecast</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                <div>
                  <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                    <span>Demand Shift:</span>
                    <strong className="text-purple-300">{growthRatePct > 0 ? `+${growthRatePct}%` : `${growthRatePct}%`}</strong>
                  </div>
                  <input
                    type="range"
                    min={-30}
                    max={30}
                    value={growthRatePct}
                    onChange={(e) => setGrowthRatePct(Number(e.target.value))}
                    className="w-full accent-purple-400 cursor-pointer"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                    <span>Price Change:</span>
                    <strong className="text-cyan-300">{priceChangePct > 0 ? `+${priceChangePct}%` : `${priceChangePct}%`}</strong>
                  </div>
                  <input
                    type="range"
                    min={-20}
                    max={20}
                    value={priceChangePct}
                    onChange={(e) => setPriceChangePct(Number(e.target.value))}
                    className="w-full accent-cyan-400 cursor-pointer"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                    <span>Marketing Budget Shift:</span>
                    <strong className="text-emerald-300">{marketingBudgetPct > 0 ? `+${marketingBudgetPct}%` : `${marketingBudgetPct}%`}</strong>
                  </div>
                  <input
                    type="range"
                    min={-40}
                    max={50}
                    value={marketingBudgetPct}
                    onChange={(e) => setMarketingBudgetPct(Number(e.target.value))}
                    className="w-full accent-emerald-400 cursor-pointer"
                  />
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 3. Main Workspace Body: Chart, Performance & AI Insights */}
      {activeRun ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <div className={chatOpen ? 'lg:col-span-8 space-y-6' : 'lg:col-span-12 space-y-6'}>
            {/* View Switcher Tabs: Main Forecast, Backtest Evaluation, Scenarios */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-2">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setActiveChartTab('forecast')}
                  className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 text-xs font-semibold transition ${
                    activeChartTab === 'forecast'
                      ? 'bg-cyan-500/20 text-cyan-200 border border-cyan-500/40 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <TrendingUp size={13} />
                  Forecast & Confidence Bands
                </button>

                <button
                  onClick={() => setActiveChartTab('backtest')}
                  className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 text-xs font-semibold transition ${
                    activeChartTab === 'backtest'
                      ? 'bg-amber-500/20 text-amber-200 border border-amber-500/40 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <Activity size={13} />
                  Holdout Backtest Curves
                </button>

                <button
                  onClick={() => setActiveChartTab('scenarios')}
                  className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 text-xs font-semibold transition ${
                    activeChartTab === 'scenarios'
                      ? 'bg-purple-500/20 text-purple-200 border border-purple-500/40 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <Compass size={13} />
                  Business Decision Scenarios
                </button>
              </div>

              <span className="text-[11px] text-slate-400">
                Champion: <strong>{activeRun.model_type.toUpperCase()}</strong> • Evaluated on Holdout Window
              </span>
            </div>

            {/* Plotly Interactive Visualization */}
            <div className="glass rounded-3xl p-6 border border-slate-800 space-y-4">
              <div className="h-[420px]">
                {activeChartTab === 'forecast' && (
                  <Plot
                    data={[
                      // 95% Upper Bound
                      {
                        x: activeRun.predictions.map((p) => p.date.slice(0, 10)),
                        y: activeRun.confidence_intervals?.upper_95 || [],
                        type: 'scatter',
                        mode: 'lines',
                        name: '95% Upper Bound',
                        line: { color: 'rgba(34, 211, 238, 0.2)', width: 1, dash: 'dot' },
                        showlegend: true,
                      },
                      // 80% Upper Bound
                      {
                        x: activeRun.predictions.map((p) => p.date.slice(0, 10)),
                        y: activeRun.confidence_intervals?.upper_80 || [],
                        type: 'scatter',
                        mode: 'lines',
                        name: '80% Upper Bound',
                        line: { color: 'rgba(34, 211, 238, 0.4)', width: 1 },
                        showlegend: false,
                      },
                      // 80% Lower Bound with Fill
                      {
                        x: activeRun.predictions.map((p) => p.date.slice(0, 10)),
                        y: activeRun.confidence_intervals?.lower_80 || [],
                        type: 'scatter',
                        mode: 'lines',
                        name: '80% Confidence Band',
                        line: { color: 'rgba(34, 211, 238, 0.4)', width: 1 },
                        fill: 'tonexty',
                        fillcolor: 'rgba(34, 211, 238, 0.12)',
                        showlegend: true,
                      },
                      // 95% Lower Bound
                      {
                        x: activeRun.predictions.map((p) => p.date.slice(0, 10)),
                        y: activeRun.confidence_intervals?.lower_95 || [],
                        type: 'scatter',
                        mode: 'lines',
                        name: '95% Lower Bound',
                        line: { color: 'rgba(34, 211, 238, 0.2)', width: 1, dash: 'dot' },
                        showlegend: false,
                      },
                      // Forecast Mean Line
                      {
                        x: activeRun.predictions.map((p) => p.date.slice(0, 10)),
                        y: activeRun.predictions.map((p) => p.value),
                        type: 'scatter',
                        mode: 'lines+markers',
                        name: `Forecast (${activeRun.model_type})`,
                        line: { color: '#22d3ee', width: 3 },
                        marker: { size: 6, color: '#22d3ee' },
                      },
                    ] as never}
                    layout={{
                      autosize: true,
                      margin: { l: 50, r: 20, t: 30, b: 50 },
                      paper_bgcolor: 'transparent',
                      plot_bgcolor: 'transparent',
                      font: { color: '#94a3b8', size: 11 },
                      xaxis: { gridcolor: '#1e293b' },
                      yaxis: { title: { text: activeRun.target_column }, gridcolor: '#1e293b' },
                      legend: { orientation: 'h', y: 1.15, x: 0 },
                    } as never}
                    useResizeHandler
                    style={{ width: '100%', height: '100%' }}
                    config={{ displayModeBar: false, responsive: true }}
                  />
                )}

                {activeChartTab === 'backtest' && activeRun.backtest_results && (
                  <Plot
                    data={[
                      // Actual Holdout
                      {
                        x: activeRun.backtest_results.dates.map((d) => d.slice(0, 10)),
                        y: activeRun.backtest_results.actual,
                        type: 'scatter',
                        mode: 'lines+markers',
                        name: 'Actual Holdout',
                        line: { color: '#f8fafc', width: 3 },
                        marker: { size: 7, color: '#f8fafc' },
                      },
                      // Candidate Models
                      ...Object.entries(activeRun.backtest_results.models || {}).map(([mKey, vals], idx) => {
                        const colors = ['#22d3ee', '#f59e0b', '#a855f7', '#10b981', '#3b82f6']
                        return {
                          x: activeRun.backtest_results!.dates.map((d) => d.slice(0, 10)),
                          y: vals,
                          type: 'scatter',
                          mode: 'lines+markers',
                          name: mKey.replace('_', ' ').toUpperCase(),
                          line: { color: colors[idx % colors.length], width: mKey === activeRun.model_type ? 2.5 : 1.5, dash: mKey === activeRun.model_type ? 'solid' : 'dot' },
                          marker: { size: 5 },
                        }
                      }),
                    ] as never}
                    layout={{
                      autosize: true,
                      margin: { l: 50, r: 20, t: 30, b: 50 },
                      paper_bgcolor: 'transparent',
                      plot_bgcolor: 'transparent',
                      font: { color: '#94a3b8', size: 11 },
                      xaxis: { gridcolor: '#1e293b' },
                      yaxis: { title: { text: activeRun.target_column }, gridcolor: '#1e293b' },
                      legend: { orientation: 'h', y: 1.15, x: 0 },
                    } as never}
                    useResizeHandler
                    style={{ width: '100%', height: '100%' }}
                    config={{ displayModeBar: false, responsive: true }}
                  />
                )}

                {activeChartTab === 'scenarios' && activeRun.scenarios && (
                  <Plot
                    data={[
                      {
                        x: activeRun.predictions.map((p) => p.date.slice(0, 10)),
                        y: activeRun.scenarios.baseline.values,
                        type: 'scatter',
                        mode: 'lines+markers',
                        name: 'Statistical Baseline',
                        line: { color: '#22d3ee', width: 2.5 },
                      },
                      {
                        x: activeRun.predictions.map((p) => p.date.slice(0, 10)),
                        y: activeRun.scenarios.optimistic.values,
                        type: 'scatter',
                        mode: 'lines+markers',
                        name: 'Optimistic Case (+)',
                        line: { color: '#10b981', width: 2, dash: 'dash' },
                      },
                      {
                        x: activeRun.predictions.map((p) => p.date.slice(0, 10)),
                        y: activeRun.scenarios.pessimistic.values,
                        type: 'scatter',
                        mode: 'lines+markers',
                        name: 'Conservative Case (-)',
                        line: { color: '#ef4444', width: 2, dash: 'dash' },
                      },
                      {
                        x: activeRun.predictions.map((p) => p.date.slice(0, 10)),
                        y: activeRun.scenarios.custom.values,
                        type: 'scatter',
                        mode: 'lines+markers',
                        name: 'User What-If Scenario',
                        line: { color: '#a855f7', width: 3 },
                      },
                    ] as never}
                    layout={{
                      autosize: true,
                      margin: { l: 50, r: 20, t: 30, b: 50 },
                      paper_bgcolor: 'transparent',
                      plot_bgcolor: 'transparent',
                      font: { color: '#94a3b8', size: 11 },
                      xaxis: { gridcolor: '#1e293b' },
                      yaxis: { title: { text: activeRun.target_column }, gridcolor: '#1e293b' },
                      legend: { orientation: 'h', y: 1.15, x: 0 },
                    } as never}
                    useResizeHandler
                    style={{ width: '100%', height: '100%' }}
                    config={{ displayModeBar: false, responsive: true }}
                  />
                )}
              </div>
            </div>

            {/* Performance Metric Cards */}
            <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
              <div className="glass rounded-2xl p-3 border border-slate-800 space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase">Holdout WAPE</span>
                <p className="text-lg font-bold text-cyan-300">
                  {activeRun.metrics.wape !== undefined ? `${activeRun.metrics.wape}%` : '—'}
                </p>
                <p className="text-[10px] text-slate-500">Scale-aware error</p>
              </div>

              <div className="glass rounded-2xl p-3 border border-slate-800 space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase">Holdout MAE</span>
                <p className="text-lg font-bold text-slate-100">
                  {activeRun.metrics.mae !== undefined ? activeRun.metrics.mae.toLocaleString() : '—'}
                </p>
                <p className="text-[10px] text-slate-500">Mean absolute error</p>
              </div>

              <div className="glass rounded-2xl p-3 border border-slate-800 space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase">Holdout RMSE</span>
                <p className="text-lg font-bold text-slate-100">
                  {activeRun.metrics.rmse !== undefined ? activeRun.metrics.rmse.toLocaleString() : '—'}
                </p>
                <p className="text-[10px] text-slate-500">Root mean squared</p>
              </div>

              <div className="glass rounded-2xl p-3 border border-slate-800 space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase">MASE Benchmark</span>
                <p className="text-lg font-bold text-slate-100">
                  {activeRun.metrics.mase !== undefined ? activeRun.metrics.mase : '—'}
                </p>
                <p className="text-[10px] text-slate-500">&lt; 1.0 beats naive</p>
              </div>

              <div className="glass rounded-2xl p-3 border border-slate-800 space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase">R² Coefficient</span>
                <p className="text-lg font-bold text-slate-100">
                  {activeRun.metrics.r2 !== undefined ? activeRun.metrics.r2 : '—'}
                </p>
                <p className="text-[10px] text-slate-500">Explained variance</p>
              </div>

              <div className="glass rounded-2xl p-3 border border-slate-800 space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase">Vs Naive Baseline</span>
                <p className="text-lg font-bold text-emerald-300">
                  {activeRun.metrics.wape_improvement_vs_naive_pct !== undefined
                    ? `${activeRun.metrics.wape_improvement_vs_naive_pct > 0 ? '+' : ''}${activeRun.metrics.wape_improvement_vs_naive_pct}%`
                    : '—'}
                </p>
                <p className="text-[10px] text-slate-500">Holdout advantage</p>
              </div>
            </div>

            {/* Candidate Model Comparison Table */}
            {activeRun.candidate_models && activeRun.candidate_models.length > 0 && (
              <div className="glass rounded-3xl p-6 border border-slate-800 space-y-3">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                  <Award size={14} className="text-amber-400" />
                  Candidate Model Comparison (Chronological Holdout Evaluation)
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase">
                      <tr>
                        <th className="py-2.5 px-3">Model</th>
                        <th className="py-2.5 px-3">WAPE (%)</th>
                        <th className="py-2.5 px-3">MAE</th>
                        <th className="py-2.5 px-3">RMSE</th>
                        <th className="py-2.5 px-3">MASE</th>
                        <th className="py-2.5 px-3">Vs Naive</th>
                        <th className="py-2.5 px-3">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-200">
                      {activeRun.candidate_models.map((cand) => (
                        <tr key={cand.key} className="hover:bg-slate-800/30">
                          <td className="py-2.5 px-3 font-semibold text-slate-100 flex items-center gap-2">
                            {cand.name}
                            {cand.key === activeRun.model_type && (
                              <span className="rounded-full bg-cyan-400/20 text-cyan-300 text-[9px] px-2 py-0.5 font-bold border border-cyan-400/30">
                                Champion
                              </span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 font-bold text-cyan-300">{cand.metrics?.wape}%</td>
                          <td className="py-2.5 px-3">{cand.metrics?.mae?.toLocaleString()}</td>
                          <td className="py-2.5 px-3">{cand.metrics?.rmse?.toLocaleString()}</td>
                          <td className="py-2.5 px-3">{cand.metrics?.mase ?? '—'}</td>
                          <td className="py-2.5 px-3">
                            <span className={cand.metrics?.wape_improvement_vs_naive_pct && cand.metrics.wape_improvement_vs_naive_pct > 0 ? 'text-emerald-400' : 'text-slate-400'}>
                              {cand.metrics?.wape_improvement_vs_naive_pct !== undefined ? `${cand.metrics.wape_improvement_vs_naive_pct > 0 ? '+' : ''}${cand.metrics.wape_improvement_vs_naive_pct}%` : '—'}
                            </span>
                          </td>
                          <td className="py-2.5 px-3">
                            <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300">
                              {cand.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Business Decision Scenarios Comparison Cards */}
            {activeRun.scenarios && (
              <div className="glass rounded-3xl p-6 border border-slate-800 space-y-4">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                  <Compass size={14} className="text-purple-400" />
                  Business Scenario Projected Totals
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                  {Object.entries(activeRun.scenarios).map(([scKey, sc]: [string, ForecastScenario]) => (
                    <div
                      key={scKey}
                      className={`rounded-2xl p-4 border space-y-1.5 ${
                        scKey === 'baseline'
                          ? 'border-cyan-500/30 bg-cyan-950/10'
                          : scKey === 'optimistic'
                          ? 'border-emerald-500/30 bg-emerald-950/10'
                          : scKey === 'pessimistic'
                          ? 'border-red-500/30 bg-red-950/10'
                          : 'border-purple-500/30 bg-purple-950/10'
                      }`}
                    >
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                        {sc.name}
                      </span>
                      <p className="text-xl font-bold text-slate-100">
                        {sc.total.toLocaleString()}
                      </p>
                      <p className={`text-[11px] font-semibold ${sc.delta_vs_baseline >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {sc.delta_vs_baseline === 0
                          ? 'Baseline Point'
                          : `${sc.delta_vs_baseline > 0 ? '+' : ''}${sc.delta_vs_baseline.toLocaleString()} (${sc.delta_pct_vs_baseline}%)`}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Forecasting Insights Narrative */}
            {activeRun.insights && (
              <div className="glass rounded-3xl p-6 border border-slate-800 space-y-4">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                  <Brain size={14} className="text-cyan-400" />
                  Automated Forecasting Insights & Strategic Milestones
                </h3>

                <div className="space-y-3 text-xs text-slate-200 leading-relaxed">
                  <p className="text-sm font-semibold text-slate-100">
                    {activeRun.insights.executive_summary}
                  </p>
                  <p className="text-slate-400">
                    {activeRun.insights.pattern_description}
                  </p>
                  <p className="text-purple-300">
                    {activeRun.insights.uncertainty_assessment}
                  </p>
                </div>

                <div className="pt-2 border-t border-slate-800/60 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Recommended Actions:</span>
                    <ul className="space-y-1.5 text-xs text-slate-300">
                      {activeRun.insights.recommendations?.map((r, i) => (
                        <li key={i} className="flex items-start gap-1.5">
                          <span className="text-cyan-400 font-bold">•</span>
                          <span>{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="space-y-2">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Model Assumptions & Limitations:</span>
                    <ul className="space-y-1.5 text-xs text-slate-400">
                      {activeRun.insights.limitations?.map((l, i) => (
                        <li key={i} className="flex items-start gap-1.5">
                          <span>-</span>
                          <span>{l}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* AI Forecasting Copilot Sidebar */}
          {chatOpen && (
            <div className="lg:col-span-4 glass rounded-3xl p-5 border border-slate-800 space-y-4 h-[750px] flex flex-col justify-between">
              <div className="space-y-3 flex-1 flex flex-col overflow-hidden">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <Brain size={16} className="text-purple-400" />
                    <h3 className="text-xs font-bold text-slate-100 uppercase tracking-wider">
                      Forecasting Copilot
                    </h3>
                  </div>
                  <button onClick={() => setChatOpen(false)} className="text-slate-400 hover:text-slate-200">
                    <X size={14} />
                  </button>
                </div>

                {/* Preset Suggestions */}
                <div className="flex flex-wrap gap-1.5">
                  {[
                    'Explain uncertainty in this prediction',
                    'Compare with baseline',
                    'Show peak and trough milestones',
                    'What features could improve accuracy?',
                  ].map((pill) => (
                    <button
                      key={pill}
                      onClick={() => handleSendChat(pill)}
                      className="rounded-lg bg-slate-900/80 hover:bg-slate-800 px-2.5 py-1 text-[10px] font-medium text-slate-300 border border-slate-800 transition"
                    >
                      {pill}
                    </button>
                  ))}
                </div>

                {/* Message Log */}
                <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs">
                  {chatMessages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`rounded-2xl p-3.5 space-y-1.5 leading-relaxed ${
                        msg.sender === 'user'
                          ? 'bg-purple-500/20 text-purple-100 ml-6 border border-purple-500/30'
                          : 'bg-slate-900/90 text-slate-200 mr-4 border border-slate-800'
                      }`}
                    >
                      <div className="flex items-center justify-between text-[10px] opacity-70">
                        <span>{msg.sender === 'user' ? 'You' : 'Forecasting Copilot'}</span>
                        <span>{msg.timestamp}</span>
                      </div>
                      <div className="whitespace-pre-wrap">{msg.text}</div>
                    </div>
                  ))}
                  {chatLoading && (
                    <div className="rounded-2xl p-3 bg-slate-900/60 text-slate-400 text-xs flex items-center gap-2">
                      <RefreshCw size={13} className="animate-spin text-purple-400" />
                      <span>Synthesizing mathematical time-series evidence...</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Chat Input */}
              <div className="pt-2 border-t border-slate-800 flex items-center gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendChat()}
                  placeholder="Ask about forecast trend, WAPE score, or uncertainty..."
                  className="flex-1 rounded-xl border border-slate-800 bg-slate-900/90 px-3 py-2 text-xs text-slate-200 focus:border-purple-400 focus:outline-none"
                />
                <button
                  onClick={() => handleSendChat()}
                  disabled={!chatInput.trim() || chatLoading}
                  className="rounded-xl bg-purple-500 p-2 text-white hover:bg-purple-400 transition disabled:opacity-50"
                >
                  <Send size={14} />
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="glass rounded-3xl p-16 text-center space-y-3">
          <TrendingUp size={28} className="mx-auto text-cyan-400" />
          <h3 className="text-base font-semibold text-slate-200">No Forecast Trained Yet</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Select your date column and target metric above, then click <strong>"Train & Evaluate"</strong> to generate predictive projections with uncertainty confidence bands.
          </p>
        </div>
      )}
    </div>
  )
}
