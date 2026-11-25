import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  ArrowUpRight,
  Award,
  BarChart3,
  Bookmark,
  BookmarkCheck,
  Brain,
  CheckCircle2,
  ChevronDown,
  Clock,
  Compass,
  Copy,
  Database,
  Download,
  ExternalLink,
  Eye,
  FileCheck,
  FileSpreadsheet,
  FileText,
  Filter,
  HelpCircle,
  Layers,
  Lightbulb,
  MessageSquare,
  Play,
  Presentation,
  RefreshCw,
  Send,
  Share2,
  ShieldAlert,
  Sparkles,
  TrendingDown,
  TrendingUp,
  X,
  Zap,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client'
import { forecastService } from '../services/forecastService'
import { reportService } from '../services/reportService'
import type { ForecastingRecommendation } from '../types/forecast'
import ChartRenderer from '../visualization-studio/ChartRenderer'

// --- Interfaces ---
interface InsightItem {
  id: number
  category:
    | 'overview'
    | 'quality'
    | 'statistical'
    | 'distribution'
    | 'trend'
    | 'correlation'
    | 'categorical'
    | 'comparative'
    | 'anomaly'
    | 'performance'
    | 'predictive'
    | 'opportunity'
    | 'risk'
  chart_spec?: Record<string, unknown> | null
  priority: 'high' | 'medium' | 'low'
  title: string
  explanation: string
  supporting_metrics?: Record<string, any>
  evidence_data?: {
    type?: string
    chart_type?: string
    x_axis?: string
    y_axis?: string
    rows?: Record<string, any>[]
    chart_spec?: Record<string, unknown> | null
    [key: string]: unknown
  }
  methodology?: string
  confidence_score: number
  confidence_justification?: string
  recommended_action?: string
  action_type?: string
  action_payload?: Record<string, any> | null
  source_columns?: string[]
  status: 'new' | 'saved' | 'dismissed' | 'resolved'
  is_stale: boolean
  created_at?: string
}

interface ExecutiveSummary {
  project_overview: string
  category_coverage?: Array<{ category: string; label?: string; status?: string; count?: number; message?: string }> | Record<string, { label?: string; status?: string; count?: number; message?: string }>
  key_metrics: { label: string; value: string; subtext: string }[]
  key_findings: { title: string; explanation: string; category: string; priority: string }[]
  opportunities: string[]
  risks: string[]
  recommended_next_actions: string[]
  limitations_and_uncertainties: string[]
  generated_at: string
}

interface AutomatedEDA {
  dataset_name: string
  row_count: number
  column_count: number
  quality_score: number
  quality_methodology: Record<string, any>
  schema: {
    name: string
    dtype: string
    inferred_type: string
    role: string
    unique_count: number
    missing_count: number
    missing_percent: number
    sample_values: any[]
  }[]
  numeric_stats: Record<string, any>
  distributions: Record<string, { bins: number[]; counts: number[] }>
  categorical_breakdowns: Record<string, { category: string; count: number; percentage: number }[]>
  correlations: Record<string, Record<string, number>>
  notable_correlations: {
    col1: string
    col2: string
    correlation: number
    strength: string
    direction: string
  }[]
  time_trend?: {
    date_column: string
    target_column: string
    labels: string[]
    values: number[]
  }
}

interface ProjectInsightsResponse {
  dataset_id: number
  dataset_name: string
  dataset_fingerprint: string
  is_stale: boolean
  cached: boolean
  executive_summary: ExecutiveSummary
  eda: AutomatedEDA
  quality_score: number
  insights: InsightItem[]
}

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
  sources?: string[]
  timestamp: string
  chart_config?: Record<string, unknown> | null
}

export default function ProjectInsightsPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const datasetId = Number(id) || 1

  // Navigation & View State
  const [activeTab, setActiveTab] = useState<'summary' | 'eda' | 'insights' | 'deep_dive' | 'reports'>('summary')
  const [insightCategoryFilter, setInsightCategoryFilter] = useState<string>('all')
  const [insightPriorityFilter, setInsightPriorityFilter] = useState<string>('all')
  const [insightStatusFilter, setInsightStatusFilter] = useState<'all' | 'active' | 'saved' | 'dismissed'>('active')

  // Dataset List & Data
  const [datasets, setDatasets] = useState<DatasetOption[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [insightsData, setInsightsData] = useState<ProjectInsightsResponse | null>(null)

  // Modal / Evidence Drawer
  const [selectedInsight, setSelectedInsight] = useState<InsightItem | null>(null)
  const [actionSuccessMessage, setActionSuccessMessage] = useState('')

  // AI Chat Sidebar
  const [chatOpen, setChatOpen] = useState(false)
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: 'init',
      sender: 'ai',
      text: "Hello! I'm your Project Intelligence Analyst. Ask me anything about this dataset's trends, data quality, or underlying mathematical evidence.",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ])

  // Deep-Dive ANOVA / Anomaly State
  const [groupCol, setGroupCol] = useState('')
  const [metricCol, setMetricCol] = useState('')
  const [anovaResult, setAnovaResult] = useState<any>(null)
  const [runningAnova, setRunningAnova] = useState(false)

  // Report Share State
  const [shareUrl, setShareUrl] = useState('')
  const [copiedShare, setCopiedShare] = useState(false)

  // Forecasting Recommendation State
  const [forecastRecommendation, setForecastRecommendation] = useState<ForecastingRecommendation | null>(null)

  // Report Export State
  const [exportMenuOpen, setExportMenuOpen] = useState(false)

  const handleExportDirect = async (format: 'pdf' | 'xlsx' | 'docx' | 'pptx' | 'json') => {
    setExportMenuOpen(false)
    try {
      await reportService.downloadDirect(
        `/reports/insights/${datasetId}/download?format=${format}`,
        `Analyticx_Insights_dataset_${datasetId}.${format}`
      )
      setActionSuccessMessage(`Downloaded Project Insights ${format.toUpperCase()} successfully.`)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const handleExportPackage = async () => {
    setExportMenuOpen(false)
    try {
      await reportService.exportPackage({
        dataset_id: datasetId,
        selected_categories: ['insights', 'statistical', 'forecast', 'cleaning'],
      })
      setActionSuccessMessage('Complete Project Intelligence Package (ZIP) downloaded.')
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  // Single Insight Export State & Handler
  const [singleExportingId, setSingleExportingId] = useState<number | null>(null)
  const [modalExportMenuOpen, setModalExportMenuOpen] = useState(false)

  const handleExportSingleInsight = async (
    insight: InsightItem,
    format: 'pdf' | 'csv' | 'json' | 'docx' = 'pdf'
  ) => {
    try {
      setSingleExportingId(insight.id)
      setModalExportMenuOpen(false)
      await reportService.exportSingleInsight(insight, format)
      setActionSuccessMessage(`Exported '${insight.title}' as ${format.toUpperCase()} dossier.`)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSingleExportingId(null)
    }
  }

  // 1. Fetch available datasets
  useEffect(() => {
    api
      .get<DatasetOption[]>('/datasets')
      .then((res) => {
        setDatasets(res.data)
      })
      .catch(() => {})
  }, [])

  // 2. Fetch project insights for current dataset
  const fetchInsights = async (forceRefresh = false) => {
    if (!datasetId) return
    if (forceRefresh) setRefreshing(true)
    else setLoading(true)
    setError('')
    try {
      const url = forceRefresh
        ? `/project-insights/${datasetId}/refresh`
        : `/project-insights/${datasetId}`
      const res = await (forceRefresh
        ? api.post<ProjectInsightsResponse>(url)
        : api.get<ProjectInsightsResponse>(url))
      setInsightsData(res.data)

      // Set initial deep-dive column defaults
      if (res.data.eda?.schema) {
        const cat = res.data.eda.schema.find((s) => s.role === 'Categorical Dimension')
        const num = res.data.eda.schema.find((s) => s.role === 'Metric')
        if (cat) setGroupCol(cat.name)
        if (num) setMetricCol(num.name)
      }

      // Proactively inspect forecasting recommendation
      try {
        const rec = await forecastService.getRecommendation(datasetId)
        setForecastRecommendation(rec)
      } catch {
        setForecastRecommendation(null)
      }
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchInsights(false)
  }, [datasetId])

  // 3. Filtered insights feed
  const filteredInsights = useMemo(() => {
    if (!insightsData?.insights) return []
    return insightsData.insights.filter((item) => {
      if (insightCategoryFilter !== 'all' && item.category !== insightCategoryFilter) return false
      if (insightPriorityFilter !== 'all' && item.priority !== insightPriorityFilter) return false
      if (insightStatusFilter === 'active' && item.status === 'dismissed') return false
      if (insightStatusFilter === 'saved' && item.status !== 'saved') return false
      if (insightStatusFilter === 'dismissed' && item.status !== 'dismissed') return false
      return true
    })
  }, [insightsData, insightCategoryFilter, insightPriorityFilter, insightStatusFilter])

  // 4. Update Insight Status (Save / Dismiss)
  const handleUpdateStatus = async (insightId: number, newStatus: 'saved' | 'dismissed' | 'new') => {
    try {
      await api.patch(`/project-insights/${datasetId}/insights/${insightId}`, { status: newStatus })
      setInsightsData((prev) => {
        if (!prev) return prev
        return {
          ...prev,
          insights: prev.insights.map((i) => (i.id === insightId ? { ...i, status: newStatus } : i)),
        }
      })
      if (selectedInsight?.id === insightId) {
        setSelectedInsight((prev) => (prev ? { ...prev, status: newStatus } : null))
      }
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  // 5. Run Insight Action (Create Chart / ANOVA test)
  const handleRunAction = async (insight: InsightItem) => {
    if (!insight.action_type) return
    setActionSuccessMessage('')
    try {
      const res = await api.post(`/project-insights/${datasetId}/action`, {
        action_type: insight.action_type,
        insight_id: insight.id,
        payload: insight.action_payload,
      })
      if (res.data.success) {
        if (insight.action_type === 'create_chart') {
          setActionSuccessMessage(`Widget successfully created on Dashboard #${res.data.dashboard_id}!`)
        } else if (insight.action_type === 'deeper_analysis') {
          setActiveTab('deep_dive')
          setAnovaResult(res.data)
        } else if (insight.action_type === 'remediate_data') {
          navigate(res.data.action_payload?.route || `/data-prep/${datasetId}`)
        }
      }
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  // 6. Deep Dive ANOVA test trigger
  const handleRunAnova = async () => {
    if (!groupCol || !metricCol) return
    setRunningAnova(true)
    setError('')
    try {
      const res = await api.post(`/project-insights/${datasetId}/action`, {
        action_type: 'deeper_analysis',
        payload: { group_column: groupCol, value_column: metricCol },
      })
      setAnovaResult(res.data)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setRunningAnova(false)
    }
  }

  // 7. AI Chat submit
  const handleSendChat = async (questionText?: string) => {
    const q = (questionText || chatInput).trim()
    if (!q || chatLoading) return

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
      const res = await api.post<{ question: string; answer: string; grounded_sources: string[]; chart_config?: Record<string, unknown> | null }>(
        `/project-insights/${datasetId}/chat`,
        { question: q }
      )
      const aiMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: res.data.answer,
        sources: res.data.grounded_sources,
        chart_config: res.data.chart_config ?? null,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }
      setChatMessages((prev) => [...prev, aiMsg])
    } catch (err) {
      const errReply: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: `Error analyzing project context: ${getErrorMessage(err)}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }
      setChatMessages((prev) => [...prev, errReply])
    } finally {
      setChatLoading(false)
    }
  }

  // 8. Multi-Format Report Downloads
  const downloadFile = async (format: 'pdf' | 'docx' | 'pptx') => {
    try {
      const res = await api.post(`/reports/dataset/${datasetId}/${format}`, {}, { responseType: 'blob' })
      const blob = new Blob([res.data])
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Analyticx_Project_Intelligence_${datasetId}.${format}`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  // 9. Generate Sharable Link
  const handleShareReport = async () => {
    try {
      const res = await api.post<{ share_token: string; share_url: string }>(
        `/reports/dataset/${datasetId}/share`,
        {
          title: `Project Intelligence Briefing (${insightsData?.dataset_name || `Dataset #${datasetId}`})`,
          executive_summary: insightsData?.executive_summary?.project_overview || 'Automated project audit.',
          recommendations: insightsData?.executive_summary?.recommended_next_actions || [],
        }
      )
      const fullUrl = `${window.location.origin}${res.data.share_url}`
      setShareUrl(fullUrl)
      navigator.clipboard.writeText(fullUrl)
      setCopiedShare(true)
      setTimeout(() => setCopiedShare(false), 3000)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  return (
    <div className="space-y-6 pb-16">
      {/* 1. Header with Context Switcher & Intelligence Badges */}
      <div className="glass rounded-3xl p-6 border border-slate-800 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-500/20 to-cyan-500/20 text-purple-300 border border-purple-500/30">
              <Sparkles size={24} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-purple-400">
                  Advanced Mode
                </span>
                <span className="text-slate-500">•</span>
                <span className="text-xs text-slate-400">Context-Aware AI Intelligence</span>
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-100 flex items-center gap-3">
                Project Insights Workspace
              </h1>
            </div>
          </div>

          {/* Dataset Switcher & Re-analyze Controls */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 rounded-2xl border border-slate-800 bg-slate-900/80 px-3 py-1.5">
              <Database size={14} className="text-cyan-400" />
              <select
                value={datasetId}
                onChange={(e) => navigate(`/insights/${e.target.value}`)}
                className="bg-transparent text-xs font-semibold text-slate-200 focus:outline-none cursor-pointer"
              >
                {datasets.map((d) => (
                  <option key={d.id} value={d.id} className="bg-slate-900 text-slate-200">
                    {d.name} ({d.row_count} rows)
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={() => fetchInsights(true)}
              disabled={refreshing}
              className="inline-flex items-center gap-2 rounded-2xl border border-purple-500/30 bg-purple-500/10 px-4 py-2 text-xs font-semibold text-purple-200 hover:bg-purple-500/20 transition disabled:opacity-50"
            >
              <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
              {refreshing ? 'Re-Analyzing...' : 'Re-Analyze Project'}
            </button>

            {/* Quick Export Dropdown */}
            <div className="relative">
              <button
                onClick={() => setExportMenuOpen(!exportMenuOpen)}
                className="inline-flex items-center gap-2 rounded-2xl border border-slate-700 bg-slate-800/80 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition"
                title="Download verified reports and packages"
              >
                <Download size={14} />
                Download Report
              </button>

              {exportMenuOpen && (
                <div className="absolute right-0 top-full mt-2 z-50 w-64 rounded-2xl border border-slate-700 bg-slate-900/95 p-2 shadow-2xl backdrop-blur-xl space-y-1">
                  <button
                    onClick={() => handleExportDirect('pdf')}
                    className="w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-slate-200 hover:bg-slate-800 transition"
                  >
                    <FileText size={14} className="text-red-400" />
                    <div>
                      <p className="font-semibold">Executive PDF Briefing</p>
                      <p className="text-[10px] text-slate-400">Formal document with quality audits</p>
                    </div>
                  </button>

                  <button
                    onClick={() => handleExportDirect('xlsx')}
                    className="w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-slate-200 hover:bg-slate-800 transition"
                  >
                    <FileSpreadsheet size={14} className="text-emerald-400" />
                    <div>
                      <p className="font-semibold">Excel Workbook (.xlsx)</p>
                      <p className="text-[10px] text-slate-400">Executive summary & findings table</p>
                    </div>
                  </button>

                  <button
                    onClick={() => handleExportDirect('docx')}
                    className="w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-slate-200 hover:bg-slate-800 transition"
                  >
                    <FileText size={14} className="text-blue-400" />
                    <div>
                      <p className="font-semibold">Microsoft Word (.docx)</p>
                      <p className="text-[10px] text-slate-400">Editable OpenXML report</p>
                    </div>
                  </button>

                  <button
                    onClick={() => handleExportDirect('pptx')}
                    className="w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-slate-200 hover:bg-slate-800 transition"
                  >
                    <Presentation size={14} className="text-purple-400" />
                    <div>
                      <p className="font-semibold">PowerPoint Slides (.pptx)</p>
                      <p className="text-[10px] text-slate-400">Management deck with variance tables</p>
                    </div>
                  </button>

                  <button
                    onClick={handleExportPackage}
                    className="w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-slate-200 hover:bg-slate-800 transition border-t border-slate-800/80 mt-1 pt-1.5"
                  >
                    <Zap size={14} className="text-indigo-400" />
                    <div>
                      <p className="font-semibold">Project Intelligence Package (ZIP)</p>
                      <p className="text-[10px] text-slate-400">Bundles all reports, stats, and data</p>
                    </div>
                  </button>
                </div>
              )}
            </div>

            <button
              onClick={() => setChatOpen(!chatOpen)}
              className={`inline-flex items-center gap-2 rounded-2xl px-4 py-2 text-xs font-semibold transition ${
                chatOpen
                  ? 'bg-cyan-400 text-slate-950 shadow-md shadow-cyan-950'
                  : 'border border-cyan-500/30 bg-cyan-500/10 text-cyan-200 hover:bg-cyan-500/20'
              }`}
            >
              <MessageSquare size={14} />
              AI Analyst Chat
            </button>
          </div>
        </div>

        {/* Status Metadata Bar */}
        {insightsData && (
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-800/60 text-[11px] text-slate-400">
            <div className="flex flex-wrap items-center gap-4">
              <span className="flex items-center gap-1.5">
                <FileSpreadsheet size={13} className="text-slate-400" />
                <strong>{insightsData.dataset_name}</strong>
              </span>
              <span className="flex items-center gap-1.5">
                <Layers size={13} className="text-slate-400" />
                {insightsData.eda?.row_count?.toLocaleString()} Records • {insightsData.eda?.column_count} Dimensions
              </span>
              <span className="flex items-center gap-1.5 font-mono text-[10px] text-slate-500">
                Fingerprint: {insightsData.dataset_fingerprint.slice(0, 8)}...
              </span>
            </div>

            <div className="flex items-center gap-3">
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-bold border ${
                  insightsData.quality_score >= 85
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                    : 'border-amber-500/30 bg-amber-500/10 text-amber-300'
                }`}
              >
                <Award size={11} />
                Quality: {insightsData.quality_score}%
              </span>
              <span className="flex items-center gap-1 text-slate-500">
                <Clock size={11} />
                {insightsData.cached ? 'Loaded from cache' : 'Fresh analysis'}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Notifications / Alerts */}
      {error && (
        <div className="rounded-2xl border border-red-500/40 bg-red-500/10 p-4 text-xs text-red-200 flex items-center gap-2">
          <AlertCircle size={16} className="text-red-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {actionSuccessMessage && (
        <div className="rounded-2xl border border-emerald-500/40 bg-emerald-500/10 p-4 text-xs text-emerald-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
            <span>{actionSuccessMessage}</span>
          </div>
          <button onClick={() => setActionSuccessMessage('')} className="text-slate-400 hover:text-slate-200">
            <X size={14} />
          </button>
        </div>
      )}

      {/* 2. Workspace Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('summary')}
          className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition ${
            activeTab === 'summary'
              ? 'bg-purple-500/20 text-purple-200 border border-purple-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Compass size={14} className="text-purple-400" />
          Executive Summary
        </button>

        <button
          onClick={() => setActiveTab('eda')}
          className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition ${
            activeTab === 'eda'
              ? 'bg-cyan-500/20 text-cyan-200 border border-cyan-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <BarChart3 size={14} className="text-cyan-400" />
          Automated EDA & Quality
        </button>

        <button
          onClick={() => setActiveTab('insights')}
          className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition ${
            activeTab === 'insights'
              ? 'bg-emerald-500/20 text-emerald-200 border border-emerald-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Lightbulb size={14} className="text-emerald-400" />
          Business & Proactive Insights
          {insightsData?.insights && (
            <span className="rounded-full bg-slate-900 px-1.5 py-0.2 text-[10px] font-bold text-slate-300">
              {insightsData.insights.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('deep_dive')}
          className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition ${
            activeTab === 'deep_dive'
              ? 'bg-blue-500/20 text-blue-200 border border-blue-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Zap size={14} className="text-blue-400" />
          Deep-Dive Statistical Analysis
        </button>

        <button
          onClick={() => setActiveTab('reports')}
          className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition ${
            activeTab === 'reports'
              ? 'bg-amber-500/20 text-amber-200 border border-amber-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Presentation size={14} className="text-amber-400" />
          Reports & Public Share
        </button>
      </div>

      {/* 3. Main Body Content by Active Tab */}
      {loading ? (
        <div className="glass rounded-3xl p-16 text-center space-y-3">
          <RefreshCw size={28} className="mx-auto text-purple-400 animate-spin" />
          <h3 className="text-base font-semibold text-slate-200">Analyzing Project & Ingesting Context...</h3>
          <p className="text-xs text-slate-400">Computing automated exploratory statistics, quality metrics, and evidence-grounded insights.</p>
        </div>
      ) : insightsData ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left/Main Workspace Column */}
          <div className={chatOpen ? 'lg:col-span-8 space-y-6' : 'lg:col-span-12 space-y-6'}>
            {/* VIEW A: EXECUTIVE SUMMARY */}
            {activeTab === 'summary' && (
              <div className="space-y-6">
                {/* 4 Metric Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {insightsData.executive_summary?.key_metrics?.map((km, idx) => (
                    <div key={idx} className="glass rounded-2xl p-4 border border-slate-800 space-y-1">
                      <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">{km.label}</span>
                      <p className="text-xl font-bold text-slate-100">{km.value}</p>
                      <p className="text-[10px] text-slate-500">{km.subtext}</p>
                    </div>
                  ))}
                </div>

                {/* Project Overview Statement */}
                <div className="glass rounded-3xl p-6 border border-slate-800 space-y-3">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                    <Compass size={14} className="text-purple-400" />
                    Executive Overview & Business Scope
                  </h3>
                  <p className="text-sm text-slate-200 leading-relaxed">
                    {insightsData.executive_summary?.project_overview}
                  </p>
                </div>

                {/* Proactive Forecasting Opportunity Card */}
                {forecastRecommendation && forecastRecommendation.has_recommendation && (
                  <div className="glass rounded-3xl p-6 border border-cyan-500/30 bg-gradient-to-r from-cyan-950/20 via-slate-900/60 to-purple-950/20 space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className="rounded-2xl bg-cyan-500/20 p-2.5 text-cyan-300 border border-cyan-500/30">
                          <TrendingUp size={20} />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="rounded-full bg-cyan-500/20 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-cyan-300 border border-cyan-500/30">
                              Proactive AI Recommendation
                            </span>
                            <span className="text-[11px] text-slate-400">Chronological Momentum</span>
                          </div>
                          <h3 className="text-sm font-bold text-slate-100 mt-0.5">
                            {forecastRecommendation.title}
                          </h3>
                        </div>
                      </div>

                      <Link
                        to={`/forecasting/${datasetId}`}
                        className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-4 py-2 text-xs font-bold text-white shadow-lg shadow-cyan-500/20 hover:from-cyan-400 hover:to-blue-500 transition"
                      >
                        <TrendingUp size={14} />
                        Launch Forecasting Lab
                        <ArrowRight size={13} />
                      </Link>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed">
                      {forecastRecommendation.message}
                    </p>

                    <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-slate-800/60 text-xs">
                      <span className="rounded-xl bg-slate-900/90 px-3 py-1.5 text-slate-300 border border-slate-800 flex items-center gap-2">
                        <span className="text-slate-500">Date Axis:</span>
                        <strong className="text-cyan-300 font-mono">{forecastRecommendation.date_column}</strong>
                      </span>
                      <span className="rounded-xl bg-slate-900/90 px-3 py-1.5 text-slate-300 border border-slate-800 flex items-center gap-2">
                        <span className="text-slate-500">Target Metric:</span>
                        <strong className="text-purple-300 font-mono">{forecastRecommendation.target_column}</strong>
                      </span>
                      <span className="rounded-xl bg-slate-900/90 px-3 py-1.5 text-slate-300 border border-slate-800 flex items-center gap-2">
                        <span className="text-slate-500">Cadence:</span>
                        <strong className="text-emerald-300 font-mono">{forecastRecommendation.frequency}</strong>
                      </span>
                      <span className="rounded-xl bg-slate-900/90 px-3 py-1.5 text-slate-300 border border-slate-800 flex items-center gap-2">
                        <span className="text-slate-500">Observations:</span>
                        <strong className="text-amber-300">{forecastRecommendation.readiness?.row_count} records</strong>
                      </span>
                    </div>
                  </div>
                )}

                {/* Top Findings Grid */}
                <div className="space-y-3">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                    Discovered Priority Findings
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {insightsData.executive_summary?.key_findings?.map((kf, idx) => (
                      <div key={idx} className="glass rounded-2xl p-5 border border-slate-800 space-y-2 flex flex-col justify-between">
                        <div className="space-y-1.5">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-purple-400">
                            {kf.category} • {kf.priority} priority
                          </span>
                          <h4 className="text-xs font-bold text-slate-100 leading-snug">{kf.title}</h4>
                          <p className="text-[11px] text-slate-400 leading-relaxed line-clamp-3">{kf.explanation}</p>
                        </div>
                        <button
                          onClick={() => {
                            setActiveTab('insights')
                            const match = insightsData.insights.find((i) => i.title === kf.title)
                            if (match) setSelectedInsight(match)
                          }}
                          className="pt-2 text-[11px] font-semibold text-cyan-400 hover:text-cyan-300 inline-flex items-center gap-1"
                        >
                          View Full Evidence <ArrowRight size={12} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Opportunities vs Risks */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="glass rounded-3xl p-6 border border-emerald-500/20 bg-emerald-950/10 space-y-3">
                    <h4 className="text-xs font-bold text-emerald-300 uppercase tracking-wider flex items-center gap-2">
                      <TrendingUp size={14} className="text-emerald-400" />
                      Strategic Growth Opportunities
                    </h4>
                    <ul className="space-y-2 text-xs text-slate-300">
                      {insightsData.executive_summary?.opportunities?.map((opp, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-emerald-400 font-bold">•</span>
                          <span>{opp}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="glass rounded-3xl p-6 border border-red-500/20 bg-red-950/10 space-y-3">
                    <h4 className="text-xs font-bold text-red-300 uppercase tracking-wider flex items-center gap-2">
                      <ShieldAlert size={14} className="text-red-400" />
                      Identified Risks & Vulnerabilities
                    </h4>
                    <ul className="space-y-2 text-xs text-slate-300">
                      {insightsData.executive_summary?.risks?.map((risk, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-red-400 font-bold">•</span>
                          <span>{risk}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {insightsData.executive_summary?.category_coverage && (
                  <div className="glass rounded-3xl p-6 border border-slate-800 space-y-3">
                    <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                      <Layers size={14} className="text-cyan-400" />
                      12-Category Analytical Coverage
                    </h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2.5">
                      {(Array.isArray(insightsData.executive_summary.category_coverage)
                        ? insightsData.executive_summary.category_coverage
                        : Object.entries(insightsData.executive_summary.category_coverage).map(([category, info]) => ({ category, ...info }))
                      ).map((info) => {
                        const covered = info.status === 'available' || info.status === 'covered'
                        return (
                          <div key={info.category} className="rounded-xl border border-slate-800 bg-slate-900/60 p-2.5 text-xs">
                            <div className="flex items-center justify-between gap-1 font-semibold capitalize text-slate-200">
                              <span className="truncate">{info.label || info.category}</span>
                              <span className={covered ? 'text-emerald-400' : 'text-slate-500'}>
                                {info.count ?? 0}
                              </span>
                            </div>
                            <p className="mt-1 line-clamp-2 text-[10px] text-slate-400" title={info.message || info.status}>
                              {covered ? 'Insight verified' : info.message || 'Insufficient data'}
                            </p>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

                {/* Next Steps & Limitations */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="glass rounded-3xl p-6 border border-slate-800 space-y-3">
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                      <CheckCircle2 size={14} className="text-cyan-400" />
                      Recommended Next Actions
                    </h4>
                    <ul className="space-y-2 text-xs text-slate-300">
                      {insightsData.executive_summary?.recommended_next_actions?.map((act, idx) => (
                        <li key={idx}>{act}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="glass rounded-3xl p-6 border border-slate-800 space-y-3">
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                      <HelpCircle size={14} className="text-slate-400" />
                      Data Limitations & Uncertainties
                    </h4>
                    <ul className="space-y-2 text-xs text-slate-400">
                      {insightsData.executive_summary?.limitations_and_uncertainties?.map((lim, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span>-</span>
                          <span>{lim}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* VIEW B: AUTOMATED EDA & QUALITY */}
            {activeTab === 'eda' && (
              <div className="space-y-6">
                {/* Data Quality Methodology Card */}
                <div className="glass rounded-3xl p-6 border border-slate-800 space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                        <Award size={16} className="text-emerald-400" />
                        Transparent Data Quality Score: {insightsData.eda?.quality_score}%
                      </h3>
                      <p className="text-xs text-slate-400 mt-1">
                        Computed with proportional deductions across missingness, duplicate rows, zero-variance columns, and IQR outliers.
                      </p>
                    </div>
                    <Link
                      to={`/data-prep/${datasetId}`}
                      className="inline-flex items-center gap-2 rounded-xl bg-emerald-500/20 border border-emerald-500/40 px-3 py-1.5 text-xs font-semibold text-emerald-200 hover:bg-emerald-500/30 transition"
                    >
                      <FileCheck size={13} />
                      Clean in Data Prep Studio
                    </Link>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2">
                    <div className="rounded-xl bg-slate-900/60 p-3 border border-slate-800">
                      <span className="text-[10px] text-slate-500 font-semibold uppercase">Missing Cells</span>
                      <p className="text-base font-bold text-slate-200">{insightsData.eda?.quality_methodology?.null_cells}</p>
                      <p className="text-[10px] text-red-400">-{insightsData.eda?.quality_methodology?.missing_deduction} pts</p>
                    </div>
                    <div className="rounded-xl bg-slate-900/60 p-3 border border-slate-800">
                      <span className="text-[10px] text-slate-500 font-semibold uppercase">Duplicate Rows</span>
                      <p className="text-base font-bold text-slate-200">{insightsData.eda?.quality_methodology?.duplicate_rows}</p>
                      <p className="text-[10px] text-red-400">-{insightsData.eda?.quality_methodology?.duplicate_deduction} pts</p>
                    </div>
                    <div className="rounded-xl bg-slate-900/60 p-3 border border-slate-800">
                      <span className="text-[10px] text-slate-500 font-semibold uppercase">Extreme Outliers</span>
                      <p className="text-base font-bold text-slate-200">{insightsData.eda?.quality_methodology?.outlier_points}</p>
                      <p className="text-[10px] text-red-400">-{insightsData.eda?.quality_methodology?.outlier_deduction} pts</p>
                    </div>
                    <div className="rounded-xl bg-slate-900/60 p-3 border border-slate-800">
                      <span className="text-[10px] text-slate-500 font-semibold uppercase">Single Value Cols</span>
                      <p className="text-base font-bold text-slate-200">{insightsData.eda?.quality_methodology?.single_value_columns?.length || 0}</p>
                      <p className="text-[10px] text-slate-400">0 variance</p>
                    </div>
                  </div>
                </div>

                {/* Schema & Data Dictionary */}
                <div className="glass rounded-3xl p-6 border border-slate-800 space-y-4">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                    <Database size={14} className="text-cyan-400" />
                    Dataset Schema & Data Dictionary
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase">
                        <tr>
                          <th className="py-2.5 px-3">Column Name</th>
                          <th className="py-2.5 px-3">Inferred Role</th>
                          <th className="py-2.5 px-3">Data Type</th>
                          <th className="py-2.5 px-3">Unique Values</th>
                          <th className="py-2.5 px-3">Missingness</th>
                          <th className="py-2.5 px-3">Sample Values</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 text-slate-200">
                        {insightsData.eda?.schema?.map((col) => (
                          <tr key={col.name} className="hover:bg-slate-800/30">
                            <td className="py-2.5 px-3 font-semibold text-slate-100">{col.name}</td>
                            <td className="py-2.5 px-3">
                              <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-cyan-300">
                                {col.role}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 font-mono text-[11px] text-slate-400">{col.dtype}</td>
                            <td className="py-2.5 px-3">{col.unique_count}</td>
                            <td className="py-2.5 px-3">
                              {col.missing_count > 0 ? (
                                <span className="text-amber-400 font-semibold">{col.missing_count} ({col.missing_percent}%)</span>
                              ) : (
                                <span className="text-emerald-400">0%</span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 font-mono text-[10px] text-slate-400 truncate max-w-xs">
                              {col.sample_values?.join(', ')}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Descriptive Statistics Table */}
                {Object.keys(insightsData.eda?.numeric_stats || {}).length > 0 && (
                  <div className="glass rounded-3xl p-6 border border-slate-800 space-y-4">
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                      <BarChart3 size={14} className="text-purple-400" />
                      Descriptive Numeric Metrics (5-Number Summary & Skew)
                    </h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead className="border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase">
                          <tr>
                            <th className="py-2 px-3">Metric</th>
                            <th className="py-2 px-3">Mean</th>
                            <th className="py-2 px-3">Std Dev</th>
                            <th className="py-2 px-3">Min</th>
                            <th className="py-2 px-3">Q1 (25%)</th>
                            <th className="py-2 px-3">Median</th>
                            <th className="py-2 px-3">Q3 (75%)</th>
                            <th className="py-2 px-3">Max</th>
                            <th className="py-2 px-3">IQR</th>
                            <th className="py-2 px-3">Skew</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 text-slate-200">
                          {Object.entries(insightsData.eda.numeric_stats).map(([k, st]: [string, any]) => (
                            <tr key={k} className="hover:bg-slate-800/30">
                              <td className="py-2.5 px-3 font-semibold text-slate-100">{k}</td>
                              <td className="py-2.5 px-3">{st.mean?.toLocaleString()}</td>
                              <td className="py-2.5 px-3">{st.std?.toLocaleString()}</td>
                              <td className="py-2.5 px-3">{st.min?.toLocaleString()}</td>
                              <td className="py-2.5 px-3">{st.p25?.toLocaleString()}</td>
                              <td className="py-2.5 px-3 font-bold text-cyan-300">{st.median?.toLocaleString()}</td>
                              <td className="py-2.5 px-3">{st.p75?.toLocaleString()}</td>
                              <td className="py-2.5 px-3">{st.max?.toLocaleString()}</td>
                              <td className="py-2.5 px-3">{st.iqr?.toLocaleString()}</td>
                              <td className="py-2.5 px-3">{st.skew}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* VIEW C: BUSINESS & PROACTIVE INSIGHTS FEED */}
            {activeTab === 'insights' && (
              <div className="space-y-6">
                {/* Filter Controls Bar */}
                <div className="glass rounded-2xl p-4 border border-slate-800 flex flex-wrap items-center justify-between gap-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-semibold text-slate-400 flex items-center gap-1.5 mr-2">
                      <Filter size={13} />
                      Filter Status:
                    </span>
                    {(['active', 'saved', 'dismissed', 'all'] as const).map((st) => (
                      <button
                        key={st}
                        onClick={() => setInsightStatusFilter(st)}
                        className={`rounded-xl px-3 py-1 text-xs font-medium capitalize transition ${
                          insightStatusFilter === st
                            ? 'bg-purple-500 text-white shadow-sm'
                            : 'bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                        }`}
                      >
                        {st}
                      </button>
                    ))}
                  </div>

                  <div className="flex items-center gap-3">
                    <select
                      value={insightCategoryFilter}
                      onChange={(e) => setInsightCategoryFilter(e.target.value)}
                      className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 focus:outline-none"
                    >
                      <option value="all">All Categories</option>
                      <option value="overview">Overview</option>
                      <option value="quality">Quality</option>
                      <option value="statistical">Statistical</option>
                      <option value="distribution">Distribution</option>
                      <option value="trend">Trend</option>
                      <option value="correlation">Correlation</option>
                      <option value="categorical">Categorical</option>
                      <option value="comparative">Comparative</option>
                      <option value="anomaly">Anomaly</option>
                      <option value="performance">Performance</option>
                      <option value="predictive">Predictive</option>
                      <option value="opportunity">Opportunity</option>
                      <option value="risk">Risk</option>
                    </select>

                    <select
                      value={insightPriorityFilter}
                      onChange={(e) => setInsightPriorityFilter(e.target.value)}
                      className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 focus:outline-none"
                    >
                      <option value="all">All Priorities</option>
                      <option value="high">High Priority</option>
                      <option value="medium">Medium Priority</option>
                      <option value="low">Low Priority</option>
                    </select>
                  </div>
                </div>

                {/* Proactive Forecasting Banner in Insights Tab */}
                {forecastRecommendation && forecastRecommendation.has_recommendation && (
                  <div className="glass rounded-3xl p-5 border border-cyan-500/30 bg-gradient-to-r from-cyan-950/30 via-slate-900/50 to-slate-950 flex flex-wrap items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className="rounded-xl bg-cyan-500/20 p-2 text-cyan-300">
                        <TrendingUp size={18} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400">
                            Proactive AI Pipeline Opportunity
                          </span>
                        </div>
                        <h4 className="text-xs font-bold text-slate-100">
                          {forecastRecommendation.title}
                        </h4>
                        <p className="text-[11px] text-slate-400 mt-0.5 max-w-xl">
                          {forecastRecommendation.message}
                        </p>
                      </div>
                    </div>

                    <Link
                      to={`/forecasting/${datasetId}`}
                      className="inline-flex items-center gap-1.5 rounded-xl bg-cyan-500/20 border border-cyan-500/40 px-3.5 py-1.5 text-xs font-bold text-cyan-200 hover:bg-cyan-500/30 transition shadow-sm"
                    >
                      <TrendingUp size={13} />
                      Launch Forecasting Lab
                      <ArrowRight size={12} />
                    </Link>
                  </div>
                )}

                {/* Insights Cards Feed */}
                <div className="space-y-4">
                  {filteredInsights.length === 0 ? (
                    <div className="glass rounded-3xl p-12 text-center space-y-2">
                      <Lightbulb size={24} className="mx-auto text-slate-500" />
                      <p className="text-sm font-semibold text-slate-300">No insights matching active filters.</p>
                      <p className="text-xs text-slate-500">Try adjusting the status or category filters above.</p>
                    </div>
                  ) : (
                    filteredInsights.map((ins) => (
                      <div
                        key={ins.id}
                        className="glass rounded-3xl p-6 border border-slate-800 hover:border-slate-700 transition space-y-4"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <span
                                className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase ${
                                  ins.priority === 'high'
                                    ? 'bg-red-500/10 text-red-400 border border-red-500/30'
                                    : ins.priority === 'medium'
                                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                                    : 'bg-blue-500/10 text-blue-400 border border-blue-500/30'
                                }`}
                              >
                                {ins.priority} Priority
                              </span>
                              <span className="rounded-full bg-slate-900 px-2 py-0.5 text-[10px] font-semibold text-slate-400 uppercase border border-slate-800">
                                {ins.category}
                              </span>
                              {ins.status === 'saved' && (
                                <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                                  <BookmarkCheck size={10} /> Saved
                                </span>
                              )}
                            </div>
                            <h3 className="text-base font-bold text-slate-100">{ins.title}</h3>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={() =>
                                handleUpdateStatus(ins.id, ins.status === 'saved' ? 'new' : 'saved')
                              }
                              title={ins.status === 'saved' ? 'Unsave insight' : 'Save insight'}
                              className={`rounded-xl p-2 transition ${
                                ins.status === 'saved'
                                  ? 'bg-emerald-500/20 text-emerald-300'
                                  : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                              }`}
                            >
                              <Bookmark size={15} />
                            </button>
                            <button
                              onClick={() => handleUpdateStatus(ins.id, 'dismissed')}
                              title="Dismiss insight"
                              className="rounded-xl p-2 bg-slate-900 text-slate-400 hover:text-red-300 transition"
                            >
                              <X size={15} />
                            </button>
                          </div>
                        </div>

                        {/* Explanation */}
                        <p className="text-xs text-slate-300 leading-relaxed">{ins.explanation}</p>

                        {/* Methodology & Confidence Badge */}
                        <div className="flex flex-wrap items-center justify-between gap-3 pt-1 border-t border-slate-800/50 text-[11px] text-slate-400">
                          <div className="flex items-center gap-3">
                            <span className="text-purple-300 font-semibold">
                              Confidence: {Math.round(ins.confidence_score * 100)}%
                            </span>
                            <span>•</span>
                            <span className="text-slate-500">{ins.methodology}</span>
                          </div>

                          {ins.supporting_metrics?.calculation_formula && (
                            <span className="font-mono text-[10px] bg-slate-900 px-2 py-0.5 rounded-lg border border-slate-800 text-slate-400">
                              {ins.supporting_metrics.calculation_formula}
                            </span>
                          )}
                        </div>

                        {/* Action Buttons Row */}
                        <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                          <button
                            onClick={() => setSelectedInsight(ins)}
                            className="inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-400 hover:text-cyan-300 transition"
                          >
                            <Eye size={13} />
                            View Underlying Evidence & Data
                          </button>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleExportSingleInsight(ins, 'pdf')}
                              disabled={singleExportingId === ins.id}
                              title="Download individual insight dossier (PDF)"
                              className="inline-flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-900/80 px-2.5 py-1.5 text-xs font-semibold text-slate-300 hover:border-cyan-500/50 hover:text-cyan-300 transition"
                            >
                              {singleExportingId === ins.id ? (
                                <RefreshCw size={12} className="animate-spin text-cyan-400" />
                              ) : (
                                <Download size={12} />
                              )}
                              Download Dossier
                            </button>

                            {ins.action_type && (
                              <button
                                onClick={() => handleRunAction(ins)}
                                className="inline-flex items-center gap-1.5 rounded-xl bg-purple-500/20 border border-purple-500/40 px-3 py-1.5 text-xs font-semibold text-purple-200 hover:bg-purple-500/30 transition shadow-sm"
                              >
                                <Play size={12} />
                                {ins.action_type === 'create_chart'
                                  ? 'Pin to Dashboard'
                                  : ins.action_type === 'deeper_analysis'
                                  ? 'Run Deeper Test'
                                  : ins.action_type === 'remediate_data'
                                  ? 'Fix in Data Prep'
                                  : 'Execute Action'}
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* VIEW D: DEEP-DIVE STATISTICAL ANALYSIS */}
            {activeTab === 'deep_dive' && (
              <div className="space-y-6">
                <div className="glass rounded-3xl p-6 border border-slate-800 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                        <Zap size={16} className="text-blue-400" />
                        ANOVA Group Significance Hypothesis Testing
                      </h3>
                      <p className="text-xs text-slate-400 mt-1">
                        One-way Analysis of Variance (F-test) to mathematically prove whether differences across segments are statistically significant (p &lt; 0.05).
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
                    <div>
                      <label className="text-[11px] font-semibold text-slate-400 block mb-1">
                        Categorical Group (Dimension):
                      </label>
                      <select
                        value={groupCol}
                        onChange={(e) => setGroupCol(e.target.value)}
                        className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:outline-none"
                      >
                        {insightsData.eda?.schema
                          ?.filter((s) => s.role === 'Categorical Dimension')
                          .map((c) => (
                            <option key={c.name} value={c.name}>
                              {c.name} ({c.unique_count} groups)
                            </option>
                          ))}
                      </select>
                    </div>

                    <div>
                      <label className="text-[11px] font-semibold text-slate-400 block mb-1">
                        Numeric Value (Metric):
                      </label>
                      <select
                        value={metricCol}
                        onChange={(e) => setMetricCol(e.target.value)}
                        className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:outline-none"
                      >
                        {insightsData.eda?.schema
                          ?.filter((s) => s.role === 'Metric')
                          .map((c) => (
                            <option key={c.name} value={c.name}>
                              {c.name}
                            </option>
                          ))}
                      </select>
                    </div>

                    <button
                      onClick={handleRunAnova}
                      disabled={runningAnova || !groupCol || !metricCol}
                      className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-500 py-2 px-4 text-xs font-semibold text-white hover:bg-blue-400 transition disabled:opacity-50"
                    >
                      <Play size={13} className={runningAnova ? 'animate-spin' : ''} />
                      {runningAnova ? 'Testing Hypothesis...' : 'Compute ANOVA F-Test'}
                    </button>
                  </div>

                  {/* ANOVA Result Box */}
                  {anovaResult && (
                    <div className="rounded-2xl border border-blue-500/30 bg-blue-950/20 p-5 space-y-3 mt-4">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold uppercase tracking-wider text-blue-300">
                          Statistical Test Outcome
                        </span>
                        <span
                          className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold ${
                            anovaResult.result?.significant_at_0_05
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                              : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                          }`}
                        >
                          {anovaResult.result?.significant_at_0_05 ? 'Significant (p < 0.05)' : 'Not Significant'}
                        </span>
                      </div>

                      <p className="text-xs text-slate-200 leading-relaxed font-medium">
                        {anovaResult.interpretation}
                      </p>

                      <div className="grid grid-cols-3 gap-3 pt-1 text-xs">
                        <div className="rounded-xl bg-slate-900 p-2.5 border border-slate-800">
                          <span className="text-[10px] text-slate-400">F-Statistic:</span>
                          <p className="font-bold text-slate-100">{anovaResult.result?.f_statistic ?? 'N/A'}</p>
                        </div>
                        <div className="rounded-xl bg-slate-900 p-2.5 border border-slate-800">
                          <span className="text-[10px] text-slate-400">p-value:</span>
                          <p className="font-bold text-slate-100">{anovaResult.result?.p_value ?? 'N/A'}</p>
                        </div>
                        <div className="rounded-xl bg-slate-900 p-2.5 border border-slate-800">
                          <span className="text-[10px] text-slate-400">Group Count:</span>
                          <p className="font-bold text-slate-100">{anovaResult.result?.groups ?? 'N/A'}</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* VIEW E: REPORTS & PUBLIC SHARE */}
            {activeTab === 'reports' && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* PDF Card */}
                  <div className="glass rounded-3xl p-6 border border-slate-800 space-y-4 flex flex-col justify-between">
                    <div className="space-y-2">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-400/10 text-cyan-300">
                        <FileText size={20} />
                      </div>
                      <h4 className="text-sm font-bold text-slate-100">Executive PDF Briefing</h4>
                      <p className="text-xs text-slate-400">
                        Formal document with data quality audits, top findings, and numerical traces.
                      </p>
                    </div>
                    <button
                      onClick={() => downloadFile('pdf')}
                      className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-400 py-2.5 text-xs font-semibold text-slate-950 hover:bg-cyan-300 transition"
                    >
                      <Download size={14} /> Download PDF
                    </button>
                  </div>

                  {/* Word DOCX Card */}
                  <div className="glass rounded-3xl p-6 border border-slate-800 space-y-4 flex flex-col justify-between">
                    <div className="space-y-2">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/10 text-blue-300">
                        <FileSpreadsheet size={20} />
                      </div>
                      <h4 className="text-sm font-bold text-slate-100">Microsoft Word (.docx)</h4>
                      <p className="text-xs text-slate-400">
                        Fully formatted OpenXML Word report ready for management comments and edits.
                      </p>
                    </div>
                    <button
                      onClick={() => downloadFile('docx')}
                      className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-blue-500 py-2.5 text-xs font-semibold text-white hover:bg-blue-400 transition"
                    >
                      <Download size={14} /> Download Word (.docx)
                    </button>
                  </div>

                  {/* PPTX Presentation Card */}
                  <div className="glass rounded-3xl p-6 border border-slate-800 space-y-4 flex flex-col justify-between">
                    <div className="space-y-2">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-500/10 text-purple-300">
                        <Presentation size={20} />
                      </div>
                      <h4 className="text-sm font-bold text-slate-100">PowerPoint Deck (.pptx)</h4>
                      <p className="text-xs text-slate-400">
                        Presentation-ready slides with agenda, variance tables, and action items.
                      </p>
                    </div>
                    <button
                      onClick={() => downloadFile('pptx')}
                      className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-purple-500 py-2.5 text-xs font-semibold text-white hover:bg-purple-400 transition"
                    >
                      <Download size={14} /> Download Slides (.pptx)
                    </button>
                  </div>
                </div>

                {/* Public Share Link Card */}
                <div className="glass rounded-3xl p-6 border border-slate-800 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                        <Share2 size={16} className="text-purple-400" />
                        Generate Public Sharable Intelligence Link
                      </h4>
                      <p className="text-xs text-slate-400 mt-1">
                        Share this project's findings with stakeholders and clients without requiring login.
                      </p>
                    </div>
                    <button
                      onClick={handleShareReport}
                      className="inline-flex items-center gap-2 rounded-xl bg-purple-500 py-2 px-4 text-xs font-semibold text-white hover:bg-purple-400 transition"
                    >
                      <Share2 size={13} />
                      Generate Link
                    </button>
                  </div>

                  {shareUrl && (
                    <div className="flex items-center gap-2 rounded-2xl border border-slate-800 bg-slate-900/90 p-3">
                      <input
                        type="text"
                        readOnly
                        value={shareUrl}
                        className="flex-1 bg-transparent text-xs font-mono text-cyan-300 focus:outline-none"
                      />
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(shareUrl)
                          setCopiedShare(true)
                          setTimeout(() => setCopiedShare(false), 2000)
                        }}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition"
                      >
                        <Copy size={12} />
                        {copiedShare ? 'Copied!' : 'Copy'}
                      </button>
                      <a
                        href={shareUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="p-1.5 text-slate-400 hover:text-cyan-300"
                      >
                        <ExternalLink size={15} />
                      </a>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Right AI Analyst Chat Sidebar */}
          {chatOpen && (
            <div className="lg:col-span-4 glass rounded-3xl p-5 border border-slate-800 space-y-4 h-[750px] flex flex-col justify-between">
              <div className="space-y-3 flex-1 flex flex-col overflow-hidden">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-2">
                    <Brain size={16} className="text-cyan-400" />
                    <h3 className="text-xs font-bold text-slate-100 uppercase tracking-wider">
                      Project AI Analyst
                    </h3>
                  </div>
                  <button onClick={() => setChatOpen(false)} className="text-slate-400 hover:text-slate-200">
                    <X size={14} />
                  </button>
                </div>

                {/* Chat Suggestion Pills */}
                <div className="flex flex-wrap gap-1.5">
                  {[
                    'Explain top 3 findings',
                    'Show evidence',
                    'What are the biggest risks?',
                    'What data is missing?',
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

                {/* Chat Messages Log */}
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
                        <span>{msg.sender === 'user' ? 'You' : 'AI Analyst'}</span>
                        <span>{msg.timestamp}</span>
                      </div>
                      <div className="whitespace-pre-wrap">{msg.text}</div>
                      {msg.chart_config && datasetId && (
                        <div className="mt-2 h-[220px] rounded-xl border border-slate-800 bg-slate-950/80 p-2">
                          <ChartRenderer
                            datasetId={Number(datasetId)}
                            chartType={String(msg.chart_config.chart_type || 'bar')}
                            dataMapping={(msg.chart_config.data_mapping || {}) as Record<string, string | string[]>}
                            appearance={(msg.chart_config.appearance || {}) as Record<string, unknown>}
                            title={(msg.chart_config.title as string) || undefined}
                            aggregation={(msg.chart_config.aggregation as string) || 'sum'}
                          />
                        </div>
                      )}
                      {msg.sources && msg.sources.length > 0 && (
                        <div className="pt-1 text-[10px] text-cyan-300 font-mono">
                          Sources: {msg.sources.join(' • ')}
                        </div>
                      )}
                    </div>
                  ))}
                  {chatLoading && (
                    <div className="rounded-2xl p-3 bg-slate-900/60 text-slate-400 text-xs flex items-center gap-2">
                      <RefreshCw size={13} className="animate-spin text-cyan-400" />
                      <span>Reasoning over project context & calculation ground truth...</span>
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
                  placeholder="Ask about project findings, formulas, or risks..."
                  className="flex-1 rounded-xl border border-slate-800 bg-slate-900/90 px-3 py-2 text-xs text-slate-200 focus:border-cyan-400 focus:outline-none"
                />
                <button
                  onClick={() => handleSendChat()}
                  disabled={!chatInput.trim() || chatLoading}
                  className="rounded-xl bg-cyan-400 p-2 text-slate-950 hover:bg-cyan-300 transition disabled:opacity-50"
                >
                  <Send size={14} />
                </button>
              </div>
            </div>
          )}
        </div>
      ) : null}

      {/* 4. Evidence Inspection Modal */}
      {selectedInsight && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="glass w-full max-w-2xl rounded-3xl border border-slate-800 p-6 space-y-5 max-h-[85vh] overflow-y-auto">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-purple-400">
                  {selectedInsight.category} • {selectedInsight.priority} priority
                </span>
                <h3 className="text-lg font-bold text-slate-100">{selectedInsight.title}</h3>
              </div>
              <button
                onClick={() => setSelectedInsight(null)}
                className="rounded-xl p-1.5 text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
              >
                <X size={18} />
              </button>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">{selectedInsight.explanation}</p>

            {/* Live Chart Spec Preview */}
            {(() => {
              const spec = (selectedInsight.chart_spec || selectedInsight.evidence_data?.chart_spec || selectedInsight.action_payload) as Record<string, unknown> | null | undefined
              const chartType = spec?.chart_type as string | undefined
              const dataMapping = (spec?.data_mapping || {}) as Record<string, string | string[]>
              if (!chartType || !datasetId) return null
              return (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-400 uppercase">Supporting Visualization</span>
                    <Link to={`/datasets/${datasetId}`} className="text-cyan-400 hover:underline">
                      Inspect Underlying Records
                    </Link>
                  </div>
                  <div className="h-[260px] rounded-2xl border border-slate-800 bg-slate-950/60 p-2">
                    <ChartRenderer
                      datasetId={Number(datasetId)}
                      chartType={chartType}
                      dataMapping={dataMapping}
                      appearance={(spec?.appearance || {}) as Record<string, unknown>}
                      title={(spec?.title as string) || selectedInsight.title}
                      aggregation={(spec?.aggregation as string) || 'sum'}
                    />
                  </div>
                </div>
              )
            })()}

            {/* Evidence Data Table */}
            {selectedInsight.evidence_data?.rows && selectedInsight.evidence_data.rows.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-slate-400 uppercase">Underlying Sample Evidence:</h4>
                <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/60 p-2">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-[10px] text-slate-400 uppercase">
                        {Object.keys(selectedInsight.evidence_data.rows[0]).map((k) => (
                          <th key={k} className="py-2 px-3">{k}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/40 text-slate-200">
                      {selectedInsight.evidence_data.rows.map((r, idx) => (
                        <tr key={idx} className="hover:bg-slate-900/40">
                          {Object.values(r).map((val, cIdx) => (
                            <td key={cIdx} className="py-2 px-3 font-mono">{String(val)}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Formula & Methodology */}
            <div className="rounded-2xl bg-slate-900/60 p-4 border border-slate-800 space-y-2 text-xs">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Mathematical Methodology:
              </span>
              <p className="text-slate-300">{selectedInsight.methodology}</p>
              {selectedInsight.supporting_metrics?.calculation_formula && (
                <div className="pt-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Formula:</span>
                  <p className="font-mono text-cyan-300 text-[11px] mt-0.5">
                    {selectedInsight.supporting_metrics.calculation_formula}
                  </p>
                </div>
              )}
            </div>

            {/* Action Bar */}
            <div className="flex items-center justify-between pt-2 border-t border-slate-800">
              <span className="text-xs text-slate-400">
                Confidence: <strong className="text-purple-300">{Math.round(selectedInsight.confidence_score * 100)}%</strong>
              </span>

              <div className="flex items-center gap-2">
                {/* Dossier Download Split / Menu */}
                <div className="relative">
                  <button
                    onClick={() => setModalExportMenuOpen(!modalExportMenuOpen)}
                    disabled={singleExportingId === selectedInsight.id}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-cyan-500/40 bg-cyan-500/10 px-3 py-1.5 text-xs font-semibold text-cyan-300 hover:bg-cyan-500/20 transition disabled:opacity-50"
                  >
                    {singleExportingId === selectedInsight.id ? (
                      <RefreshCw size={13} className="animate-spin" />
                    ) : (
                      <Download size={13} />
                    )}
                    <span>Download Dossier</span>
                    <ChevronDown size={11} className={`transition-transform ${modalExportMenuOpen ? 'rotate-180' : ''}`} />
                  </button>

                  {modalExportMenuOpen && (
                    <div className="absolute right-0 bottom-full mb-2 z-50 w-48 rounded-2xl border border-slate-700 bg-slate-950 p-2 shadow-2xl backdrop-blur-xl">
                      <div className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-800 mb-1">
                        Select Dossier Format
                      </div>
                      <button
                        onClick={() => handleExportSingleInsight(selectedInsight, 'pdf')}
                        className="w-full flex items-center gap-2 px-2.5 py-1.5 text-xs text-left text-slate-200 hover:bg-slate-800 rounded-xl transition"
                      >
                        <FileText size={14} className="text-red-400" />
                        Executive PDF (.pdf)
                      </button>
                      <button
                        onClick={() => handleExportSingleInsight(selectedInsight, 'docx')}
                        className="w-full flex items-center gap-2 px-2.5 py-1.5 text-xs text-left text-slate-200 hover:bg-slate-800 rounded-xl transition"
                      >
                        <FileText size={14} className="text-blue-400" />
                        Word Document (.docx)
                      </button>
                      <button
                        onClick={() => handleExportSingleInsight(selectedInsight, 'csv')}
                        className="w-full flex items-center gap-2 px-2.5 py-1.5 text-xs text-left text-slate-200 hover:bg-slate-800 rounded-xl transition"
                      >
                        <Database size={14} className="text-cyan-400" />
                        Evidence CSV (.csv)
                      </button>
                      <button
                        onClick={() => handleExportSingleInsight(selectedInsight, 'json')}
                        className="w-full flex items-center gap-2 px-2.5 py-1.5 text-xs text-left text-slate-200 hover:bg-slate-800 rounded-xl transition"
                      >
                        <FileText size={14} className="text-purple-400" />
                        Calculations JSON (.json)
                      </button>
                    </div>
                  )}
                </div>

                <button
                  onClick={() =>
                    handleUpdateStatus(selectedInsight.id, selectedInsight.status === 'saved' ? 'new' : 'saved')
                  }
                  className="rounded-xl border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition"
                >
                  {selectedInsight.status === 'saved' ? 'Unsave' : 'Save Insight'}
                </button>
                {selectedInsight.action_type && (
                  <button
                    onClick={() => {
                      handleRunAction(selectedInsight)
                      setSelectedInsight(null)
                    }}
                    className="rounded-xl bg-purple-500 px-4 py-1.5 text-xs font-semibold text-white hover:bg-purple-400 transition"
                  >
                    Execute Action
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
