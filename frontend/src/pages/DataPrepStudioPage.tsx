import {
  ArrowLeft,
  CheckCircle2,
  ChevronRight,
  Database,
  Download,
  FileSpreadsheet,
  FileText,
  Filter,
  History,
  Info,
  Layers,
  LineChart,
  MessageSquare,
  RefreshCw,
  Search,
  Sparkles,
  Table2,
  Edit2,
  Trash2,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client'
import CleaningDecisionCard from '../data-prep/CleaningDecisionCard'
import DataAnalystChatSidePanel from '../data-prep/DataAnalystChatSidePanel'
import EdaChartsView from '../data-prep/EdaChartsView'
import InsightsReportView from '../data-prep/InsightsReportView'
import QualityScoreCard from '../data-prep/QualityScoreCard'
import { dataPrepService } from '../services/dataPrepService'
import { reportService } from '../services/reportService'
import { useLiveApplicationContext } from '../contexts/LiveApplicationContext'
import type {
  CleaningRecommendation,
  Dataset,
  DatasetPreview,
  EdaReport,
  QualityReport,
  TransformationRecord,
} from '../types'

export default function DataPrepStudioPage() {
  const { id } = useParams()
  const datasetId = Number(id)

  const [dataset, setDataset] = useState<Dataset | null>(null)
  const [qualityReport, setQualityReport] = useState<QualityReport | null>(null)
  const [edaReport, setEdaReport] = useState<EdaReport | null>(null)
  const [preview, setPreview] = useState<DatasetPreview | null>(null)
  const [transformations, setTransformations] = useState<TransformationRecord[]>([])

  const [activeTab, setActiveTab] = useState<'decisions' | 'preview' | 'eda' | 'insights' | 'history'>('decisions')
  const [decisionFilter, setDecisionFilter] = useState<'all' | 'missing_values' | 'outliers' | 'duplicates' | 'formatting'>('all')
  const [focusedColumn, setFocusedColumn] = useState<string | null>(null)
  const [columnSearch, setColumnSearch] = useState('')

  const { setActiveDataset, setActiveFile, recordAction } = useLiveApplicationContext()

  const [chatOpen, setChatOpen] = useState(true)
  const [loading, setLoading] = useState(true)
  const [autoCleaning, setAutoCleaning] = useState(false)
  const [error, setError] = useState('')
  const [statusMessage, setStatusMessage] = useState('')

  useEffect(() => {
    setActiveDataset({ focusedColumn })
  }, [focusedColumn, setActiveDataset])

  // Trigger window resize when chat panel opens or closes
  useEffect(() => {
    window.dispatchEvent(new Event('resize'))
    const t1 = setTimeout(() => window.dispatchEvent(new Event('resize')), 100)
    const t2 = setTimeout(() => window.dispatchEvent(new Event('resize')), 320)
    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
    }
  }, [chatOpen])

  async function loadAllData() {
    if (!datasetId) return
    setError('')
    try {
      const [dsRes, qRes, edaRes, prevRes, transRes] = await Promise.all([
        api.get<Dataset>(`/datasets/${datasetId}`),
        dataPrepService.getQualityReport(datasetId),
        dataPrepService.getEdaReport(datasetId),
        api.get<DatasetPreview>(`/datasets/${datasetId}/preview`, { params: { limit: 100 } }),
        dataPrepService.getTransformations(datasetId),
      ])
      setDataset(dsRes.data)
      setQualityReport(qRes)
      setEdaReport(edaRes)
      setPreview(prevRes.data)
      setTransformations(transRes)

      setActiveDataset({
        datasetId: dsRes.data.id,
        datasetName: dsRes.data.name,
        version: dsRes.data.version,
        rowCount: dsRes.data.row_count,
        columnCount: dsRes.data.column_count,
        qualityScore: qRes.quality_score,
        selectedColumns: prevRes.data.columns,
        focusedColumn: focusedColumn,
        pendingDecisionsCount: qRes.recommendations.length,
      })
      setActiveFile({
        fileId: String(dsRes.data.id),
        fileName: dsRes.data.name,
        fileType: dsRes.data.original_filename?.endsWith('.pdf') ? 'pdf' : 'csv',
      })
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAllData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetId])

  async function handleApplyDecision(rec: CleaningRecommendation, strategy: string, customParam?: unknown) {
    if (!datasetId) return
    try {
      const result = await dataPrepService.applyAction(datasetId, {
        action_type: rec.issue_type,
        column: rec.column,
        strategy,
        parameters: {
          column: rec.column,
          strategy,
          constant_value: customParam,
          ...(rec.config || {}),
        },
      })
      setStatusMessage(`Applied: ${result.action.description}`)
      setTimeout(() => setStatusMessage(''), 4000)
      await loadAllData()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function handleAutoClean() {
    if (!datasetId) return
    setAutoCleaning(true)
    setError('')
    try {
      const res = await dataPrepService.autoClean(datasetId, false)
      setStatusMessage(`Auto-Clean finished: applied ${res.operations_count} operations. Quality: ${res.after.quality_score}%`)
      setTimeout(() => setStatusMessage(''), 5000)
      await loadAllData()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setAutoCleaning(false)
    }
  }

  async function handleUndo() {
    if (!datasetId) return
    try {
      const res = await dataPrepService.undo(datasetId)
      setStatusMessage(`Reverted: ${res.reverted_transformation || 'last action'}`)
      setTimeout(() => setStatusMessage(''), 4000)
      await loadAllData()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function handleExport(format: 'csv' | 'xlsx' | 'log' | 'report') {
    if (!datasetId) return
    if (format === 'report') {
      try {
        await reportService.downloadDirect(
          `/reports/statistical/${datasetId}/download?format=pdf`,
          `Analyticx_Statistical_Report_${dataset?.name || 'Dataset'}.pdf`
        )
        setStatusMessage('Statistical Report PDF downloaded.')
        setTimeout(() => setStatusMessage(''), 4000)
      } catch (err) {
        setError(getErrorMessage(err))
      }
      return
    }
    const url = dataPrepService.getExportUrl(datasetId, format)
    window.open(url, '_blank')
  }

  async function handleRenameColumn(col: string) {
    const newName = window.prompt(`Rename column "${col}" to:`, col)
    if (!newName || newName.trim() === col) return
    try {
      const result = await dataPrepService.applyAction(datasetId, {
        action_type: 'rename_column',
        column: col,
        parameters: { column: col, new_name: newName.trim() },
      })
      setStatusMessage(`Renamed: ${result.action.description}`)
      setTimeout(() => setStatusMessage(''), 4000)
      await loadAllData()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function handleDropColumn(col: string) {
    if (!window.confirm(`Are you sure you want to drop column "${col}" from the dataset?`)) return
    try {
      await dataPrepService.applyAction(datasetId, {
        action_type: 'drop_column',
        column: col,
        parameters: { column: col },
      })
      setStatusMessage(`Dropped column: ${col}`)
      setTimeout(() => setStatusMessage(''), 4000)
      await loadAllData()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center space-y-3">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-cyan-400 border-t-transparent" />
          <p className="text-sm text-slate-400">Loading AI Data Preparation & Automated EDA Studio…</p>
        </div>
      </div>
    )
  }

  if (!dataset || !qualityReport || !edaReport) {
    return (
      <div className="p-8 text-center space-y-4">
        <p className="text-red-400">Failed to load dataset details.</p>
        <Link to="/workspace" className="text-cyan-300 text-sm hover:underline">
          Back to Data Upload Center
        </Link>
      </div>
    )
  }

  // Filter recommendations
  const filteredRecs = qualityReport.recommendations.filter((rec) => {
    if (decisionFilter === 'all') return true
    return rec.issue_type === decisionFilter
  })

  // Filter columns list
  const filteredColumns = (preview?.columns || []).filter((c) =>
    c.toLowerCase().includes(columnSearch.toLowerCase())
  )

  return (
    <div className="space-y-6">
      {/* Top Header Row */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Link
            to="/workspace"
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-xs text-cyan-300 hover:border-cyan-500/50 hover:bg-slate-800 transition"
          >
            <ArrowLeft size={14} />
            Data Upload Center
          </Link>
          <span className="text-slate-600">/</span>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
            <Sparkles size={20} className="text-cyan-400" />
            AI-Guided Data Preparation & Automated EDA Studio
          </h1>
        </div>

        <div className="flex items-center gap-2">
          {statusMessage && (
            <span className="text-xs text-emerald-300 font-medium px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 animate-fade-in">
              {statusMessage}
            </span>
          )}
          <button
            onClick={() => setChatOpen((open) => !open)}
            className={`inline-flex items-center gap-2 rounded-xl border px-3.5 py-1.5 text-xs font-semibold transition ${
              chatOpen
                ? 'border-cyan-400 bg-cyan-400/10 text-cyan-200'
                : 'border-slate-700 bg-slate-900 text-slate-300 hover:border-cyan-400'
            }`}
          >
            <MessageSquare size={14} />
            {chatOpen ? 'Hide AI Analyst Chat' : 'AI Analyst Chat'}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-200">
          {error}
        </div>
      )}

      {/* 3-Panel Layout Container */}
      <div className={`transition-all duration-300 space-y-6 ${chatOpen ? 'sm:mr-[390px] xl:mr-[430px]' : 'mr-0'}`}>
        {/* Top Quality Score & Quick KPI Summary */}
        <QualityScoreCard
          qualityReport={qualityReport}
          onAutoClean={handleAutoClean}
          onUndo={handleUndo}
          autoCleaning={autoCleaning}
          hasTransformations={transformations.length > 0}
          onExport={handleExport}
        />

        {/* Studio Workspace: Left Sidebar + Center Panels */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* LEFT PANEL: Dataset Workspace (cols 1-3) */}
          <aside className="lg:col-span-3 glass rounded-3xl p-5 space-y-6">
            {/* Dataset Details */}
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">Active Dataset</span>
                <span className="rounded-full bg-cyan-500/10 border border-cyan-500/30 px-2 py-0.5 text-[10px] text-cyan-300 font-medium">
                  v{dataset.version}
                </span>
              </div>
              <h2 className="mt-1.5 text-base font-semibold text-slate-100 truncate" title={dataset.name}>
                {dataset.name}
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                {dataset.row_count.toLocaleString()} rows · {dataset.column_count} columns
              </p>
            </div>

            {/* Quick Actions */}
            <div className="space-y-2 border-t border-slate-800 pt-4">
              <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">Tools & Exports</span>
              <div className="grid grid-cols-2 gap-2 pt-1">
                <button
                  onClick={() => handleExport('csv')}
                  className="rounded-xl border border-slate-800 bg-slate-900/60 p-2 text-left text-xs text-slate-300 hover:border-slate-700 hover:bg-slate-800 transition flex items-center gap-1.5"
                >
                  <Download size={13} className="text-cyan-400" />
                  Clean CSV
                </button>
                <button
                  onClick={() => handleExport('xlsx')}
                  className="rounded-xl border border-slate-800 bg-slate-900/60 p-2 text-left text-xs text-slate-300 hover:border-slate-700 hover:bg-slate-800 transition flex items-center gap-1.5"
                >
                  <FileSpreadsheet size={13} className="text-emerald-400" />
                  Excel XLSX
                </button>
                <button
                  onClick={() => handleExport('report')}
                  className="col-span-2 rounded-xl border border-amber-500/30 bg-amber-500/10 p-2 text-left text-xs text-amber-200 hover:border-amber-400 hover:bg-amber-500/20 transition flex items-center justify-between"
                  title="Download Preprocessing & Quality Summary Report"
                >
                  <span className="flex items-center gap-1.5">
                    <FileText size={13} className="text-amber-400" />
                    Quality Summary Report
                  </span>
                  <Download size={12} className="text-amber-400" />
                </button>
                <Link
                  to={`/studio/${dataset.id}`}
                  className="rounded-xl border border-slate-800 bg-slate-900/60 p-2 text-left text-xs text-slate-300 hover:border-slate-700 hover:bg-slate-800 transition flex items-center gap-1.5"
                >
                  <LineChart size={13} className="text-purple-400" />
                  Chart Studio
                </Link>
                <Link
                  to={`/datasets/${dataset.id}`}
                  className="rounded-xl border border-slate-800 bg-slate-900/60 p-2 text-left text-xs text-slate-300 hover:border-slate-700 hover:bg-slate-800 transition flex items-center gap-1.5"
                >
                  <Table2 size={13} className="text-blue-400" />
                  Explorer
                </Link>
              </div>
            </div>

            {/* Column Overview List */}
            <div className="space-y-3 border-t border-slate-800 pt-4">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
                  Columns ({filteredColumns.length})
                </span>
                {focusedColumn && (
                  <button
                    onClick={() => setFocusedColumn(null)}
                    className="text-[10px] text-cyan-400 hover:underline"
                  >
                    Clear Focus
                  </button>
                )}
              </div>

              {/* Column search input */}
              <div className="relative">
                <Search size={13} className="absolute left-2.5 top-2.5 text-slate-500" />
                <input
                  type="text"
                  placeholder="Filter columns…"
                  value={columnSearch}
                  onChange={(e) => setColumnSearch(e.target.value)}
                  className="w-full rounded-xl border border-slate-800 bg-slate-900/80 pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 outline-none focus:border-cyan-400"
                />
              </div>

              {/* Column items */}
              <div className="max-h-80 space-y-1.5 overflow-y-auto pr-1">
                {filteredColumns.map((col) => {
                  const missing = qualityReport.missing_by_column[col]
                  const hasOutlier = qualityReport.outliers_by_column[col]
                  const isFocused = focusedColumn === col

                  return (
                    <div
                      key={col}
                      className={`group w-full rounded-xl p-2 text-left text-xs transition flex items-center justify-between ${
                        isFocused
                          ? 'border border-cyan-400/50 bg-cyan-400/15 text-cyan-200'
                          : 'border border-slate-800/60 bg-slate-900/30 text-slate-300 hover:bg-slate-800/60'
                      }`}
                    >
                      <button
                        onClick={() => setFocusedColumn(isFocused ? null : col)}
                        className="truncate font-mono flex-1 text-left"
                      >
                        {col}
                      </button>
                      <div className="flex items-center gap-1">
                        {missing && (
                          <span className="rounded bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.2 text-[9px] text-amber-300">
                            {missing.count} null
                          </span>
                        )}
                        {hasOutlier && (
                          <span className="rounded bg-rose-500/10 border border-rose-500/20 px-1.5 py-0.2 text-[9px] text-rose-300">
                            outlier
                          </span>
                        )}
                        <button
                          onClick={() => handleRenameColumn(col)}
                          className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-slate-700/80 text-slate-400 hover:text-cyan-300 transition"
                          title={`Rename column ${col}`}
                        >
                          <Edit2 size={11} />
                        </button>
                        <button
                          onClick={() => handleDropColumn(col)}
                          className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-slate-700/80 text-slate-400 hover:text-rose-400 transition"
                          title={`Drop column ${col}`}
                        >
                          <Trash2 size={11} />
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </aside>

          {/* CENTER PANEL: Data Analysis, Cleaning Decisions & EDA (cols 4-12) */}
          <main className="lg:col-span-9 space-y-6">
            {/* View Tab Navigation */}
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3 overflow-x-auto">
              <button
                onClick={() => setActiveTab('decisions')}
                className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition shrink-0 ${
                  activeTab === 'decisions'
                    ? 'bg-cyan-400 text-slate-950 shadow-md shadow-cyan-950/40'
                    : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                }`}
              >
                <Sparkles size={14} />
                Data Quality & Cleaning Decisions ({qualityReport.recommendations.length})
              </button>
              <button
                onClick={() => setActiveTab('preview')}
                className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition shrink-0 ${
                  activeTab === 'preview'
                    ? 'bg-cyan-400 text-slate-950 shadow-md shadow-cyan-950/40'
                    : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                }`}
              >
                <Table2 size={14} />
                Data Preview
              </button>
              <button
                onClick={() => setActiveTab('eda')}
                className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition shrink-0 ${
                  activeTab === 'eda'
                    ? 'bg-cyan-400 text-slate-950 shadow-md shadow-cyan-950/40'
                    : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                }`}
              >
                <LineChart size={14} />
                Automated EDA Charts
              </button>
              <button
                onClick={() => setActiveTab('insights')}
                className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition shrink-0 ${
                  activeTab === 'insights'
                    ? 'bg-cyan-400 text-slate-950 shadow-md shadow-cyan-950/40'
                    : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                }`}
              >
                <FileText size={14} />
                Line-by-Line Insights
              </button>
              <button
                onClick={() => setActiveTab('history')}
                className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition shrink-0 ${
                  activeTab === 'history'
                    ? 'bg-cyan-400 text-slate-950 shadow-md shadow-cyan-950/40'
                    : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                }`}
              >
                <History size={14} />
                Audit History ({transformations.length})
              </button>
            </div>

            {/* TAB 1: Cleaning Decisions Section */}
            {activeTab === 'decisions' && (
              <div className="space-y-4">
                {/* Decision Category Filter Chips */}
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs text-slate-400 mr-1 flex items-center gap-1">
                    <Filter size={13} /> Filter:
                  </span>
                  {(
                    [
                      { key: 'all', label: 'All Issues' },
                      { key: 'missing_values', label: 'Missing Values' },
                      { key: 'outliers', label: 'Outliers' },
                      { key: 'duplicates', label: 'Duplicates' },
                      { key: 'formatting', label: 'Formatting & Text' },
                    ] as const
                  ).map((f) => (
                    <button
                      key={f.key}
                      onClick={() => setDecisionFilter(f.key)}
                      className={`rounded-lg border px-3 py-1 text-xs font-medium transition ${
                        decisionFilter === f.key
                          ? 'border-cyan-400 bg-cyan-400/10 text-cyan-200'
                          : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:bg-slate-800'
                      }`}
                    >
                      {f.label}
                    </button>
                  ))}
                </div>

                {filteredRecs.length === 0 ? (
                  <div className="glass rounded-3xl p-12 text-center space-y-3">
                    <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-400">
                      <CheckCircle2 size={28} />
                    </div>
                    <h3 className="text-base font-semibold text-slate-100">No Quality Issues Found</h3>
                    <p className="text-xs text-slate-400 max-w-md mx-auto">
                      All checks for this category passed! Your dataset is validated and ready for advanced analysis.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {filteredRecs.map((rec) => (
                      <CleaningDecisionCard
                        key={rec.id}
                        recommendation={rec}
                        onApply={handleApplyDecision}
                        onSkip={(id) => {
                          setQualityReport({
                            ...qualityReport,
                            recommendations: qualityReport.recommendations.filter((r) => r.id !== id),
                          })
                        }}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: Data Preview Table */}
            {activeTab === 'preview' && (
              <div className="glass rounded-3xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-base font-semibold text-slate-100">Data Table Preview</h3>
                    <p className="text-xs text-slate-400">
                      {preview ? `Showing first ${preview.returned_rows} rows of ${preview.total_rows.toLocaleString()} total records.` : 'Loading preview…'}
                    </p>
                  </div>
                </div>

                {preview ? (
                  <div className="overflow-x-auto rounded-2xl border border-slate-800 max-h-[550px] overflow-y-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-900/90 text-slate-400 sticky top-0 border-b border-slate-800 z-10">
                        <tr>
                          <th className="py-2.5 px-3 font-mono text-slate-500">#</th>
                          {preview.columns.map((col) => (
                            <th key={col} className="py-2.5 px-3 font-mono text-slate-300">
                              {col}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/40">
                        {preview.rows.map((row, rIdx) => (
                          <tr key={rIdx} className="hover:bg-slate-800/30">
                            <td className="py-2 px-3 font-mono text-slate-600">{rIdx + 1}</td>
                            {preview.columns.map((col) => {
                              const val = row[col]
                              const isNull = val === null || val === undefined || val === ''
                              return (
                                <td
                                  key={col}
                                  className={`py-2 px-3 font-mono max-w-[200px] truncate ${
                                    isNull ? 'bg-amber-500/10 text-amber-300 italic font-sans' : 'text-slate-300'
                                  }`}
                                >
                                  {isNull ? 'null' : String(val)}
                                </td>
                              )
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-xs text-slate-400">No preview data available.</p>
                )}
              </div>
            )}

            {/* TAB 3: Automated EDA Charts */}
            {activeTab === 'eda' && <EdaChartsView edaReport={edaReport} />}

            {/* TAB 4: Line-by-Line Insights */}
            {activeTab === 'insights' && <InsightsReportView edaReport={edaReport} />}

            {/* TAB 5: Transformation Audit History */}
            {activeTab === 'history' && (
              <div className="glass rounded-3xl p-6 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div>
                    <h3 className="text-base font-semibold text-slate-100">Transformation History & Audit Log</h3>
                    <p className="text-xs text-slate-400">Verifiable chronological record of all data operations applied to this dataset.</p>
                  </div>
                  {transformations.length > 0 && (
                    <button
                      onClick={handleUndo}
                      className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 hover:border-slate-500 transition"
                    >
                      Undo Last Action
                    </button>
                  )}
                </div>

                {transformations.length === 0 ? (
                  <p className="text-xs text-slate-500 py-8 text-center">No transformations recorded yet on this dataset.</p>
                ) : (
                  <div className="space-y-3">
                    {transformations.map((t, idx) => (
                      <div
                        key={t.id}
                        className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-4 space-y-2 flex flex-col sm:flex-row sm:items-center sm:justify-between"
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs text-cyan-400 font-medium">#{transformations.length - idx}</span>
                            <span className="text-xs font-semibold text-slate-200">{t.description || t.transformation_type}</span>
                            <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] text-slate-400 uppercase">
                              {t.trigger_source}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-400 mt-1">
                            Rows: {t.row_count_before} → {t.row_count_after} · Applied at: {new Date(t.applied_at).toLocaleString()}
                          </p>
                        </div>
                        <span className={`text-xs font-medium px-2.5 py-1 rounded-lg ${t.status === 'applied' ? 'bg-emerald-500/10 text-emerald-300' : 'bg-slate-800 text-slate-400'}`}>
                          {t.status}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </main>
        </div>
      </div>

      {/* RIGHT PANEL: Persistent AI Data Analyst Chat */}
      {chatOpen && (
        <DataAnalystChatSidePanel
          datasetId={dataset.id}
          datasetName={dataset.name}
          focusedColumn={focusedColumn}
          onClose={() => setChatOpen(false)}
          onActionExecuted={loadAllData}
        />
      )}
    </div>
  )
}
