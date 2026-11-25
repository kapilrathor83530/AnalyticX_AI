import {
  Archive,
  BarChart3,
  Calendar,
  CheckCircle2,
  ChevronDown,
  Clock,
  Database,
  Download,
  Eye,
  FileCheck,
  FileSpreadsheet,
  FileText,
  Filter,
  Layers,
  Lightbulb,
  Plus,
  Presentation,
  RefreshCw,
  Search,
  Sliders,
  Sparkles,
  Trash2,
  TrendingUp,
  X,
  Zap,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client'
import { reportService } from '../services/reportService'
import type { ExportFormat, ReportItem, ReportType } from '../types/report'

interface DatasetOption {
  id: number
  name: string
  row_count: number
  column_count: number
}

interface FormatConfig {
  id: ExportFormat
  label: string
  ext: string
  icon: React.ReactNode
  bgClass: string
  badgeClass: string
  description: string
}

function getAvailableFormats(reportType: ReportType): FormatConfig[] {
  const commonFormats: FormatConfig[] = [
    {
      id: 'pdf',
      label: 'Adobe PDF',
      ext: 'PDF',
      icon: <FileText size={16} className="text-red-400" />,
      bgClass: 'bg-red-500/10 border border-red-500/20',
      badgeClass: 'text-red-400 border-red-500/30 bg-red-500/10',
      description: 'Print-ready executive document with styled findings & metric tables',
    },
    {
      id: 'docx',
      label: 'Microsoft Word',
      ext: 'DOCX',
      icon: <FileText size={16} className="text-blue-400" />,
      bgClass: 'bg-blue-500/10 border border-blue-500/20',
      badgeClass: 'text-blue-400 border-blue-500/30 bg-blue-500/10',
      description: 'Editable Word document with structured headings, narrative, and tables',
    },
    {
      id: 'xlsx',
      label: 'Microsoft Excel',
      ext: 'XLSX',
      icon: <FileSpreadsheet size={16} className="text-emerald-400" />,
      bgClass: 'bg-emerald-500/10 border border-emerald-500/20',
      badgeClass: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10',
      description: 'Multi-sheet styled workbook with auto-fitted columns and header styles',
    },
    {
      id: 'csv',
      label: 'Tabular Data',
      ext: 'CSV',
      icon: <Database size={16} className="text-cyan-400" />,
      bgClass: 'bg-cyan-500/10 border border-cyan-500/20',
      badgeClass: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10',
      description: 'Clean delimited text for external data pipelines and BI tools',
    },
    {
      id: 'json',
      label: 'Structured JSON',
      ext: 'JSON',
      icon: <FileText size={16} className="text-purple-400" />,
      bgClass: 'bg-purple-500/10 border border-purple-500/20',
      badgeClass: 'text-purple-400 border-purple-500/30 bg-purple-500/10',
      description: 'Complete machine-readable schema payload with analytics metrics',
    },
  ]

  if (reportType === 'insights' || reportType === 'statistical' || reportType === 'dashboard') {
    commonFormats.push({
      id: 'pptx',
      label: 'PowerPoint Deck',
      ext: 'PPTX',
      icon: <Presentation size={16} className="text-orange-400" />,
      bgClass: 'bg-orange-500/10 border border-orange-500/20',
      badgeClass: 'text-orange-400 border-orange-500/30 bg-orange-500/10',
      description: 'Executive presentation deck with management briefing slides',
    })
  }

  return commonFormats
}

function formatBytes(bytes: number): string {
  if (!bytes || bytes === 0) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function getFormatBadgeColor(format: ExportFormat): string {
  switch (format) {
    case 'pdf':
      return 'bg-red-500/10 text-red-400 border-red-500/20'
    case 'xlsx':
      return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
    case 'csv':
      return 'bg-blue-500/10 text-blue-400 border-blue-500/20'
    case 'zip':
      return 'bg-amber-500/10 text-amber-400 border-amber-500/20'
    case 'json':
      return 'bg-purple-500/10 text-purple-400 border-purple-500/20'
    case 'pptx':
      return 'bg-orange-500/10 text-orange-400 border-orange-500/20'
    case 'docx':
      return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20'
    default:
      return 'bg-slate-800 text-slate-300 border-slate-700'
  }
}

function getTypeIcon(type: ReportType) {
  switch (type) {
    case 'statistical':
      return <BarChart3 size={15} className="text-cyan-400" />
    case 'insights':
      return <Lightbulb size={15} className="text-purple-400" />
    case 'forecast':
      return <TrendingUp size={15} className="text-emerald-400" />
    case 'dashboard':
      return <Layers size={15} className="text-blue-400" />
    case 'cleaning':
      return <FileCheck size={15} className="text-amber-400" />
    case 'simulation':
      return <Sliders size={15} className="text-pink-400" />
    case 'package':
      return <Archive size={15} className="text-indigo-400" />
    default:
      return <FileText size={15} className="text-slate-400" />
  }
}

export default function ReportCenterPage() {
  const [reports, setReports] = useState<ReportItem[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  // Filters
  const [datasets, setDatasets] = useState<DatasetOption[]>([])
  const [selectedDatasetId, setSelectedDatasetId] = useState<number | 'all'>('all')
  const [selectedType, setSelectedType] = useState<string>('all')
  const [selectedFormat, setSelectedFormat] = useState<string>('all')
  const [selectedStatus, setSelectedStatus] = useState<string>('all')
  const [selectedDateRange, setSelectedDateRange] = useState<string>('all')
  const [searchTerm, setSearchTerm] = useState('')

  // Batch Selection
  const [selectedReportIds, setSelectedReportIds] = useState<number[]>([])
  const [batchDownloading, setBatchDownloading] = useState(false)

  // Modals
  const [previewReport, setPreviewReport] = useState<ReportItem | null>(null)
  const [previewSelectedFormat, setPreviewSelectedFormat] = useState<ExportFormat>('pdf')
  const [downloadModalReport, setDownloadModalReport] = useState<ReportItem | null>(null)
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null)
  const [generateModalOpen, setGenerateModalOpen] = useState(false)
  const [packageModalOpen, setPackageModalOpen] = useState(false)

  // Generate Modal Form
  const [genDatasetId, setGenDatasetId] = useState<number>(1)
  const [genType, setGenType] = useState<ReportType>('statistical')
  const [genFormat, setGenFormat] = useState<ExportFormat>('pdf')
  const [genTitle, setGenTitle] = useState('')
  const [generating, setGenerating] = useState(false)

  // Package Modal Form
  const [pkgDatasetId, setPkgDatasetId] = useState<number>(1)
  const [pkgCategories, setPkgCategories] = useState<{ [key: string]: boolean }>({
    statistical: true,
    insights: true,
    forecast: true,
    dashboard: true,
    cleaning: true,
  })
  const [packaging, setPackaging] = useState(false)

  // 1. Load datasets
  useEffect(() => {
    api
      .get<DatasetOption[]>('/datasets')
      .then((res) => {
        setDatasets(res.data)
        if (res.data.length > 0) {
          setGenDatasetId(res.data[0].id)
          setPkgDatasetId(res.data[0].id)
        }
      })
      .catch(() => {})
  }, [])

  // 2. Fetch reports
  const fetchReports = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await reportService.listReports({
        dataset_id: selectedDatasetId === 'all' ? undefined : selectedDatasetId,
        report_type: selectedType === 'all' ? undefined : selectedType,
        export_format: selectedFormat === 'all' ? undefined : selectedFormat,
        search: searchTerm.trim() || undefined,
        limit: 100,
      })
      setReports(data.reports)
      setTotalCount(data.total)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchReports()
  }, [selectedDatasetId, selectedType, selectedFormat])

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    fetchReports()
  }

  // Filtered reports based on Status and Date Range
  const filteredReports = useMemo(() => {
    return reports.filter((r) => {
      if (selectedStatus !== 'all' && r.status !== selectedStatus) return false
      if (selectedDateRange !== 'all' && r.created_at) {
        const d = new Date(r.created_at)
        const now = new Date()
        const diffHours = (now.getTime() - d.getTime()) / (1000 * 3600)
        if (selectedDateRange === '24h' && diffHours > 24) return false
        if (selectedDateRange === '7d' && diffHours > 24 * 7) return false
        if (selectedDateRange === '30d' && diffHours > 24 * 30) return false
      }
      return true
    })
  }, [reports, selectedStatus, selectedDateRange])

  const toggleSelectAll = () => {
    if (selectedReportIds.length === filteredReports.length && filteredReports.length > 0) {
      setSelectedReportIds([])
    } else {
      setSelectedReportIds(filteredReports.map((r) => r.id))
    }
  }

  const toggleSelectReport = (id: number) => {
    setSelectedReportIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    )
  }

  // Batch Download Selected
  const handleBatchDownload = async () => {
    if (selectedReportIds.length === 0) return
    try {
      setBatchDownloading(true)
      await reportService.batchDownloadReports(selectedReportIds)
      setSuccessMessage(`Exported ZIP archive containing ${selectedReportIds.length} selected reports.`)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBatchDownloading(false)
    }
  }

  // Batch Delete Selected
  const handleBatchDelete = async () => {
    if (selectedReportIds.length === 0) return
    if (!window.confirm(`Delete ${selectedReportIds.length} selected reports? This action cannot be undone.`)) return
    try {
      setLoading(true)
      const res = await reportService.batchDeleteReports(selectedReportIds)
      setSuccessMessage(`Deleted ${res.deleted_count} reports successfully.`)
      setSelectedReportIds([])
      fetchReports()
    } catch (err) {
      setError(getErrorMessage(err))
      setLoading(false)
    }
  }

  // Handle Download in Chosen Format
  const handleDownloadInFormat = async (item: ReportItem, format: ExportFormat) => {
    try {
      setDownloadingFormat(format)
      const cleanTitle = item.title.replace(/[^a-zA-Z0-9_-]/g, '_')
      const filename = `Analyticx_${cleanTitle}.${format}`
      await reportService.downloadSavedReport(item.id, filename, format)
      setSuccessMessage(`Downloaded '${item.title}' in ${format.toUpperCase()} format successfully.`)
      setDownloadModalReport(null)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setDownloadingFormat(null)
    }
  }

  // Handle Download Default
  const handleDownload = async (item: ReportItem) => {
    setDownloadModalReport(item)
  }

  // Handle Delete
  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this report from the archive?')) return
    try {
      await reportService.deleteReport(id)
      setReports((prev) => prev.filter((r) => r.id !== id))
      setTotalCount((prev) => Math.max(0, prev - 1))
      setSuccessMessage('Report deleted successfully.')
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  // Handle Regenerate
  const handleRegenerate = async (item: ReportItem) => {
    try {
      setLoading(true)
      await reportService.generateReport({
        dataset_id: item.dataset_id,
        report_type: item.report_type,
        export_format: item.export_format,
        title: item.title,
        parameters: item.parameters,
      })
      setSuccessMessage(`Regenerated '${item.title}' with latest active dataset state.`)
      fetchReports()
    } catch (err) {
      setError(getErrorMessage(err))
      setLoading(false)
    }
  }

  // Handle Generate New
  const handleGenerateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setGenerating(true)
    setError('')
    try {
      await reportService.generateReport({
        dataset_id: genDatasetId,
        report_type: genType,
        export_format: genFormat,
        title: genTitle.trim() || undefined,
      })
      setGenerateModalOpen(false)
      setGenTitle('')
      setSuccessMessage('Report generated and added to library.')
      fetchReports()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setGenerating(false)
    }
  }

  // Handle Package Export
  const handlePackageSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setPackaging(true)
    setError('')
    const chosen = Object.keys(pkgCategories).filter((k) => pkgCategories[k])
    if (chosen.length === 0) {
      setError('Please select at least one report category to include in package.')
      setPackaging(false)
      return
    }
    try {
      await reportService.exportPackage({
        dataset_id: pkgDatasetId,
        selected_categories: chosen,
      })
      setPackageModalOpen(false)
      setSuccessMessage('Project Package ZIP downloaded successfully.')
      fetchReports()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setPackaging(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* 1. Header Banner */}
      <div className="glass rounded-3xl p-6 border border-slate-800 flex flex-wrap items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-cyan-500/10 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-cyan-300 border border-cyan-500/20">
              Reporting & Export Center
            </span>
            <span className="text-xs text-slate-500 font-mono">Total Reports: {totalCount}</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100 flex items-center gap-2.5">
            <Archive className="text-cyan-400" size={24} />
            Enterprise Report Center & Artifact Library
          </h1>
          <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
            Centralized intelligence repository for statistical profiles, Project Insights, Forecasting Lab projections, and multi-folder executive packages.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() => setPackageModalOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 px-4 py-2 text-xs font-bold text-white shadow-lg shadow-indigo-500/20 hover:from-indigo-400 hover:to-purple-500 transition"
          >
            <Archive size={14} />
            Export Project Package (ZIP)
          </button>
          <button
            onClick={() => setGenerateModalOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-4 py-2 text-xs font-bold text-white shadow-lg shadow-cyan-500/20 hover:from-cyan-400 hover:to-blue-500 transition"
          >
            <Plus size={14} />
            Generate New Report
          </button>
        </div>
      </div>

      {/* Notifications */}
      {successMessage && (
        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/20 p-4 text-xs text-emerald-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={15} className="text-emerald-400 shrink-0" />
            <span>{successMessage}</span>
          </div>
          <button onClick={() => setSuccessMessage('')} className="text-slate-400 hover:text-slate-200">
            <X size={14} />
          </button>
        </div>
      )}

      {error && (
        <div className="rounded-2xl border border-red-500/30 bg-red-950/20 p-4 text-xs text-red-200 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError('')} className="text-slate-400 hover:text-slate-200">
            <X size={14} />
          </button>
        </div>
      )}

      {/* 2. Filter & Search Deck */}
      <div className="glass rounded-3xl p-5 border border-slate-800 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <form onSubmit={handleSearchSubmit} className="relative flex-1 min-w-[240px] max-w-md">
            <Search size={14} className="absolute left-3.5 top-3 text-slate-500" />
            <input
              type="text"
              placeholder="Search reports by title..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full rounded-xl border border-slate-800 bg-slate-900/90 pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:border-cyan-400 focus:outline-none"
            />
          </form>

          <div className="flex flex-wrap items-center gap-2.5 text-xs">
            {/* Dataset Filter */}
            <div className="flex items-center gap-1.5 bg-slate-900 px-3 py-1.5 rounded-xl border border-slate-800">
              <Database size={13} className="text-slate-400" />
              <select
                value={selectedDatasetId}
                onChange={(e) => setSelectedDatasetId(e.target.value === 'all' ? 'all' : Number(e.target.value))}
                className="bg-transparent text-slate-200 focus:outline-none"
              >
                <option value="all">All Datasets</option>
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Type Filter */}
            <div className="flex items-center gap-1.5 bg-slate-900 px-3 py-1.5 rounded-xl border border-slate-800">
              <Filter size={13} className="text-slate-400" />
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="bg-transparent text-slate-200 focus:outline-none capitalize"
              >
                <option value="all">All Report Types</option>
                <option value="statistical">Statistical Profile</option>
                <option value="insights">Project Insights</option>
                <option value="forecast">Forecasting Lab</option>
                <option value="dashboard">Dashboard Export</option>
                <option value="cleaning">Data Cleaning Log</option>
                <option value="package">Project Packages (ZIP)</option>
              </select>
            </div>

            {/* Format Filter */}
            <div className="flex items-center gap-1.5 bg-slate-900 px-3 py-1.5 rounded-xl border border-slate-800">
              <FileText size={13} className="text-slate-400" />
              <select
                value={selectedFormat}
                onChange={(e) => setSelectedFormat(e.target.value)}
                className="bg-transparent text-slate-200 focus:outline-none uppercase"
              >
                <option value="all">All Formats</option>
                <option value="pdf">PDF Document</option>
                <option value="docx">Word (DOCX)</option>
                <option value="xlsx">Excel (XLSX)</option>
                <option value="csv">CSV Table</option>
                <option value="json">JSON Metadata</option>
                <option value="pptx">PowerPoint (PPTX)</option>
                <option value="zip">ZIP Package</option>
              </select>
            </div>

            {/* Date Range Filter */}
            <div className="flex items-center gap-1.5 bg-slate-900 px-3 py-1.5 rounded-xl border border-slate-800">
              <Calendar size={13} className="text-slate-400" />
              <select
                value={selectedDateRange}
                onChange={(e) => setSelectedDateRange(e.target.value)}
                className="bg-transparent text-slate-200 focus:outline-none"
              >
                <option value="all">All Dates</option>
                <option value="24h">Last 24 Hours</option>
                <option value="7d">Last 7 Days</option>
                <option value="30d">Last 30 Days</option>
              </select>
            </div>

            {/* Status Filter */}
            <div className="flex items-center gap-1.5 bg-slate-900 px-3 py-1.5 rounded-xl border border-slate-800">
              <Clock size={13} className="text-slate-400" />
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="bg-transparent text-slate-200 focus:outline-none capitalize"
              >
                <option value="all">All Status</option>
                <option value="ready">Ready (Active)</option>
                <option value="stale">Stale (Outdated)</option>
              </select>
            </div>

            <button
              onClick={fetchReports}
              title="Refresh Report List"
              className="rounded-xl border border-slate-800 bg-slate-900 p-2 text-slate-400 hover:text-slate-200 hover:border-slate-700 transition"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin text-cyan-400' : ''} />
            </button>
          </div>
        </div>
      </div>

      {/* 3. Reports Table */}
      {loading ? (
        <div className="glass rounded-3xl p-16 text-center space-y-3">
          <RefreshCw size={26} className="mx-auto text-cyan-400 animate-spin" />
          <h3 className="text-base font-semibold text-slate-200">Loading Report Artifacts...</h3>
          <p className="text-xs text-slate-400">Querying verified report registry and persisted outputs.</p>
        </div>
      ) : filteredReports.length === 0 ? (
        <div className="glass rounded-3xl p-16 text-center space-y-3">
          <Archive size={32} className="mx-auto text-slate-600" />
          <h3 className="text-base font-semibold text-slate-300">No Reports Found</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            No generated reports match the active filter criteria. Generate your first statistical profile or export a full project package.
          </p>
          <div className="pt-2">
            <button
              onClick={() => setGenerateModalOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-xl bg-cyan-500/20 border border-cyan-500/40 px-3.5 py-1.5 text-xs font-semibold text-cyan-200 hover:bg-cyan-500/30 transition"
            >
              <Plus size={13} /> Generate First Report
            </button>
          </div>
        </div>
      ) : (
        <div className="glass rounded-3xl border border-slate-800 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 bg-slate-950/60 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-3 w-10 text-center">
                    <input
                      type="checkbox"
                      checked={filteredReports.length > 0 && selectedReportIds.length === filteredReports.length}
                      onChange={toggleSelectAll}
                      aria-label="Select all reports"
                      className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-cyan-400 h-4 w-4 cursor-pointer"
                    />
                  </th>
                  <th className="py-3 px-4">Report Title</th>
                  <th className="py-3 px-3">Type</th>
                  <th className="py-3 px-3">Format</th>
                  <th className="py-3 px-3">Associated Dataset</th>
                  <th className="py-3 px-3">Size</th>
                  <th className="py-3 px-3">Created</th>
                  <th className="py-3 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-200">
                {filteredReports.map((item) => (
                  <tr
                    key={item.id}
                    className={`hover:bg-slate-800/30 transition ${
                      selectedReportIds.includes(item.id) ? 'bg-cyan-950/15' : ''
                    }`}
                  >
                    <td className="py-3 px-3 text-center">
                      <input
                        type="checkbox"
                        checked={selectedReportIds.includes(item.id)}
                        onChange={() => toggleSelectReport(item.id)}
                        aria-label={`Select ${item.title}`}
                        className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-cyan-400 h-4 w-4 cursor-pointer"
                      />
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2.5">
                        <div className="rounded-xl bg-slate-900 p-2 border border-slate-800 shrink-0">
                          {getTypeIcon(item.report_type)}
                        </div>
                        <div>
                          <p className="font-semibold text-slate-100">{item.title}</p>
                          <p className="text-[10px] text-slate-400 font-mono">ID: #{item.id} · v{item.dataset_version}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      <span className="capitalize text-slate-300 font-medium">
                        {item.report_type.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase border ${getFormatBadgeColor(
                          item.export_format
                        )}`}
                      >
                        {item.export_format}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-slate-300">
                      <div className="flex items-center gap-1.5">
                        <Database size={12} className="text-slate-500" />
                        <span>{item.dataset_name}</span>
                      </div>
                    </td>
                    <td className="py-3 px-3 font-mono text-[11px] text-slate-400">
                      {formatBytes(item.file_size_bytes)}
                    </td>
                    <td className="py-3 px-3 text-slate-400 text-[11px]">
                      {item.created_at ? new Date(item.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : '—'}
                    </td>
                    <td className="py-3 px-3 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <div className="inline-flex rounded-lg border border-cyan-500/30 bg-cyan-500/20 shadow-sm overflow-hidden">
                          <button
                            onClick={() => setDownloadModalReport(item)}
                            title="Choose format to download report"
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-cyan-200 hover:bg-cyan-500/30 transition"
                          >
                            <Download size={12} />
                            Download
                          </button>
                          <button
                            onClick={() => setDownloadModalReport(item)}
                            title="Select download format (PDF, Word, Excel, CSV, JSON, PPTX)"
                            className="px-1.5 py-1 border-l border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/30 transition"
                          >
                            <ChevronDown size={11} />
                          </button>
                        </div>
                        <button
                          onClick={() => {
                            setPreviewReport(item)
                            setPreviewSelectedFormat(item.export_format)
                          }}
                          title="View Metadata & Preview"
                          className="rounded-lg p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
                        >
                          <Eye size={14} />
                        </button>
                        <button
                          onClick={() => handleRegenerate(item)}
                          title="Regenerate Report with Current Data"
                          className="rounded-lg p-1.5 text-slate-400 hover:text-cyan-300 hover:bg-slate-800 transition"
                        >
                          <RefreshCw size={14} />
                        </button>
                        <button
                          onClick={() => handleDelete(item.id)}
                          title="Delete Report"
                          className="rounded-lg p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-800 transition"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Floating Batch Action Bar */}
      {selectedReportIds.length > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-4 bg-slate-900/95 backdrop-blur-md border border-cyan-500/40 shadow-2xl shadow-cyan-950/50 px-5 py-3 rounded-2xl animate-in fade-in slide-in-from-bottom-5 duration-200">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-cyan-500/20 text-xs font-bold text-cyan-300 border border-cyan-500/30">
              {selectedReportIds.length}
            </span>
            <span className="text-xs font-medium text-slate-200">
              {selectedReportIds.length === 1 ? '1 report selected' : `${selectedReportIds.length} reports selected`}
            </span>
          </div>

          <div className="h-4 w-px bg-slate-800" />

          <div className="flex items-center gap-2">
            <button
              onClick={handleBatchDownload}
              disabled={batchDownloading}
              className="inline-flex items-center gap-1.5 rounded-xl bg-cyan-500 px-3.5 py-1.5 text-xs font-bold text-slate-950 hover:bg-cyan-400 transition disabled:opacity-50"
            >
              {batchDownloading ? <RefreshCw size={13} className="animate-spin" /> : <Download size={13} />}
              Download Selected (ZIP)
            </button>

            <button
              onClick={handleBatchDelete}
              className="inline-flex items-center gap-1.5 rounded-xl bg-red-500/20 border border-red-500/30 px-3.5 py-1.5 text-xs font-bold text-red-200 hover:bg-red-500/30 transition"
            >
              <Trash2 size={13} />
              Delete Selected
            </button>

            <button
              onClick={() => setSelectedReportIds([])}
              className="rounded-xl px-2.5 py-1.5 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
            >
              Clear
            </button>
          </div>
        </div>
      )}

      {/* 4. MODAL: Preview / Metadata Drawer */}
      {previewReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="glass rounded-3xl border border-slate-700 bg-slate-950 p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                {getTypeIcon(previewReport.report_type)}
                <h3 className="text-base font-bold text-slate-100">{previewReport.title}</h3>
              </div>
              <button onClick={() => setPreviewReport(null)} className="text-slate-400 hover:text-slate-200">
                <X size={16} />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-2 bg-slate-900/60 p-3 rounded-2xl border border-slate-800">
                <div>
                  <span className="text-[10px] text-slate-500 uppercase font-semibold">Report Type</span>
                  <p className="text-slate-200 font-semibold capitalize">{previewReport.report_type}</p>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 uppercase font-semibold">Format</span>
                  <p className="text-slate-200 font-semibold uppercase">{previewReport.export_format}</p>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 uppercase font-semibold">Dataset</span>
                  <p className="text-slate-200 truncate">{previewReport.dataset_name}</p>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 uppercase font-semibold">File Size</span>
                  <p className="text-slate-200 font-mono">{formatBytes(previewReport.file_size_bytes)}</p>
                </div>
              </div>

              <div>
                <span className="text-[10px] text-slate-500 uppercase font-semibold">Metadata Summary</span>
                <pre className="mt-1 bg-slate-900/90 p-3 rounded-xl border border-slate-800 text-[11px] font-mono text-slate-300 overflow-x-auto max-h-36">
                  {JSON.stringify(previewReport.report_metadata, null, 2)}
                </pre>
              </div>

              {/* Format Choice in Preview */}
              <div className="space-y-1.5 pt-2 border-t border-slate-800">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold">Choose Download Format</span>
                  <span className="text-[10px] font-mono text-cyan-400 uppercase font-bold">Selected: {previewSelectedFormat}</span>
                </div>
                <div className="grid grid-cols-3 gap-1.5">
                  {getAvailableFormats(previewReport.report_type).map((fmt) => (
                    <button
                      key={fmt.id}
                      type="button"
                      onClick={() => setPreviewSelectedFormat(fmt.id)}
                      className={`flex items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-xl border text-xs font-semibold transition ${
                        previewSelectedFormat === fmt.id
                          ? 'border-cyan-400 bg-cyan-500/20 text-cyan-200 shadow-sm shadow-cyan-500/10'
                          : 'border-slate-800 bg-slate-900/80 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                      }`}
                    >
                      {fmt.icon}
                      <span className="uppercase">{fmt.ext}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                onClick={() => setPreviewReport(null)}
                className="rounded-xl px-4 py-2 text-xs font-semibold text-slate-400 hover:bg-slate-800 transition"
              >
                Close
              </button>
              <button
                disabled={downloadingFormat !== null}
                onClick={async () => {
                  await handleDownloadInFormat(previewReport, previewSelectedFormat)
                  setPreviewReport(null)
                }}
                className="inline-flex items-center gap-1.5 rounded-xl bg-cyan-500 px-4 py-2 text-xs font-bold text-slate-950 hover:bg-cyan-400 transition"
              >
                {downloadingFormat ? <RefreshCw size={13} className="animate-spin" /> : <Download size={13} />}
                Download as {previewSelectedFormat.toUpperCase()}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 5. MODAL: Generate New Report */}
      {generateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <form
            onSubmit={handleGenerateSubmit}
            className="glass rounded-3xl border border-slate-700 bg-slate-950 p-6 max-w-lg w-full space-y-4 shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <Plus size={16} className="text-cyan-400" />
                Generate New Report
              </h3>
              <button type="button" onClick={() => setGenerateModalOpen(false)} className="text-slate-400 hover:text-slate-200">
                <X size={16} />
              </button>
            </div>

            <div className="space-y-3.5 text-xs">
              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-300">Select Dataset</label>
                <select
                  value={genDatasetId}
                  onChange={(e) => setGenDatasetId(Number(e.target.value))}
                  className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-cyan-400 focus:outline-none"
                >
                  {datasets.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.row_count} rows, {d.column_count} cols)
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-300">Report Category</label>
                <select
                  value={genType}
                  onChange={(e) => setGenType(e.target.value as ReportType)}
                  className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-cyan-400 focus:outline-none capitalize"
                >
                  <option value="statistical">Statistical Analysis Profile</option>
                  <option value="insights">Project Intelligence & Insights</option>
                  <option value="forecast">Forecasting Lab Projections</option>
                  <option value="dashboard">Dashboard Visualizations & Data</option>
                  <option value="cleaning">Data Prep & Transformation Audit</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-300">Export Format</label>
                <select
                  value={genFormat}
                  onChange={(e) => setGenFormat(e.target.value as ExportFormat)}
                  className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-cyan-400 focus:outline-none"
                >
                  <option value="pdf">PDF Document (.pdf) — Executive Layout & Print Ready</option>
                  <option value="docx">Microsoft Word (.docx) — Editable Document with Tables</option>
                  <option value="xlsx">Microsoft Excel (.xlsx) — Multi-Sheet Styled Workbook</option>
                  <option value="csv">CSV Table (.csv) — Delimited Tabular Data</option>
                  <option value="json">Structured JSON (.json) — Machine-Readable Schema</option>
                  <option value="pptx">PowerPoint (.pptx) — Executive Presentation Deck</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-300">Custom Title (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. Q4 Executive Financial Audit"
                  value={genTitle}
                  onChange={(e) => setGenTitle(e.target.value)}
                  className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:border-cyan-400 focus:outline-none"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setGenerateModalOpen(false)}
                className="rounded-xl px-4 py-2 text-xs font-semibold text-slate-400 hover:bg-slate-800 transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={generating}
                className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-4 py-2 text-xs font-bold text-white hover:from-cyan-400 hover:to-blue-500 transition disabled:opacity-50"
              >
                {generating ? <RefreshCw size={13} className="animate-spin" /> : <Plus size={13} />}
                Generate & Save
              </button>
            </div>
          </form>
        </div>
      )}

      {/* 6. MODAL: Export Project Package (ZIP) */}
      {packageModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <form
            onSubmit={handlePackageSubmit}
            className="glass rounded-3xl border border-slate-700 bg-slate-950 p-6 max-w-lg w-full space-y-4 shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <Archive size={16} className="text-indigo-400" />
                Export Complete Project Package (ZIP)
              </h3>
              <button type="button" onClick={() => setPackageModalOpen(false)} className="text-slate-400 hover:text-slate-200">
                <X size={16} />
              </button>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              Bundles all project artifacts into a structured ZIP file containing <code className="text-cyan-300">manifest.json</code>, <code className="text-cyan-300">README.txt</code>, and dedicated folders.
            </p>

            <div className="space-y-3 text-xs">
              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-300">Target Dataset</label>
                <select
                  value={pkgDatasetId}
                  onChange={(e) => setPkgDatasetId(Number(e.target.value))}
                  className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-cyan-400 focus:outline-none"
                >
                  {datasets.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.row_count} rows)
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2 pt-1">
                <label className="text-[11px] font-semibold text-slate-300">Select Report Categories to Include</label>
                <div className="space-y-2 bg-slate-900/60 p-3.5 rounded-2xl border border-slate-800">
                  {[
                    { key: 'statistical', label: 'Complete Statistical Profile (PDF, XLSX, CSV)' },
                    { key: 'insights', label: 'Project Intelligence & Empirical Insights (PDF, XLSX, JSON)' },
                    { key: 'forecast', label: 'Forecasting Lab Trajectory & Model Scenarios (PDF, CSV, XLSX)' },
                    { key: 'dashboard', label: 'Dashboard Plotted Chart Data (XLSX)' },
                    { key: 'cleaning', label: 'Data Cleaning & Transformation Audit Log (CSV)' },
                  ].map((cat) => (
                    <label key={cat.key} className="flex items-center gap-2.5 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={pkgCategories[cat.key] || false}
                        onChange={(e) =>
                          setPkgCategories((prev) => ({ ...prev, [cat.key]: e.target.checked }))
                        }
                        className="rounded border-slate-700 text-cyan-500 focus:ring-cyan-400 h-4 w-4"
                      />
                      <span className="text-slate-200 font-medium">{cat.label}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setPackageModalOpen(false)}
                className="rounded-xl px-4 py-2 text-xs font-semibold text-slate-400 hover:bg-slate-800 transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={packaging}
                className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 px-4 py-2 text-xs font-bold text-white hover:from-indigo-400 hover:to-purple-500 transition disabled:opacity-50"
              >
                {packaging ? <RefreshCw size={13} className="animate-spin" /> : <Archive size={13} />}
                Download Project ZIP Package
              </button>
            </div>
          </form>
        </div>
      )}

      {/* 6. MODAL: Choose Download Format */}
      {downloadModalReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="glass rounded-3xl border border-slate-700 bg-slate-950 p-6 max-w-xl w-full space-y-4 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400">
                  Select Download Format
                </span>
                <h3 className="text-base font-bold text-slate-100 flex items-center gap-2 mt-0.5">
                  {getTypeIcon(downloadModalReport.report_type)}
                  {downloadModalReport.title}
                </h3>
              </div>
              <button
                onClick={() => setDownloadModalReport(null)}
                className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800 transition"
              >
                <X size={16} />
              </button>
            </div>

            {/* Instruction */}
            <div className="flex items-center justify-between text-xs text-slate-400">
              <p>Choose which format to export this report in:</p>
              <span className="text-[11px] font-mono text-slate-500">
                Dataset: <span className="text-slate-300">{downloadModalReport.dataset_name}</span>
              </span>
            </div>

            {/* Formats Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-h-96 overflow-y-auto pr-1">
              {getAvailableFormats(downloadModalReport.report_type).map((fmt) => (
                <button
                  key={fmt.id}
                  disabled={downloadingFormat !== null}
                  onClick={() => handleDownloadInFormat(downloadModalReport, fmt.id)}
                  className={`flex items-start gap-3 p-3.5 rounded-2xl border text-left transition relative group ${
                    downloadModalReport.export_format === fmt.id
                      ? 'border-cyan-500/50 bg-cyan-950/20 hover:bg-cyan-900/30 shadow-sm shadow-cyan-500/10'
                      : 'border-slate-800 bg-slate-900/70 hover:border-slate-700 hover:bg-slate-800/80'
                  }`}
                >
                  <div className={`p-2.5 rounded-xl shrink-0 ${fmt.bgClass}`}>
                    {fmt.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-xs font-bold text-slate-100">{fmt.label}</span>
                      <span className={`text-[9px] font-extrabold uppercase px-1.5 py-0.5 rounded border ${fmt.badgeClass}`}>
                        {fmt.ext}
                      </span>
                      {downloadModalReport.export_format === fmt.id && (
                        <span className="text-[9px] font-semibold text-cyan-300 bg-cyan-500/10 px-1.5 py-0.5 rounded border border-cyan-500/20">
                          Original
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1 leading-snug">
                      {fmt.description}
                    </p>
                  </div>
                  <div className="shrink-0 self-center text-cyan-400">
                    {downloadingFormat === fmt.id ? (
                      <RefreshCw size={15} className="animate-spin text-cyan-400" />
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold text-cyan-300 group-hover:translate-x-0.5 transition">
                        <Download size={13} />
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-between pt-3 border-t border-slate-800 text-xs">
              <span className="text-[11px] text-slate-500">
                All formats are dynamically generated with deterministic data grounding.
              </span>
              <button
                onClick={() => setDownloadModalReport(null)}
                className="rounded-xl px-4 py-2 font-semibold text-slate-400 hover:bg-slate-800 transition"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
