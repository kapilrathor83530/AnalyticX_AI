import {
  AlertCircle,
  ArrowLeft,
  BarChart3,
  BookOpen,
  Check,
  CheckCircle2,
  Clock,
  Code2,
  Copy,
  Database,
  Download,
  FileQuestion,
  History,
  Layers,
  LineChart,
  Play,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Table as TableIcon,
  X,
  Zap,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import Plot from 'react-plotly.js'
import { Link, useParams } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client'
import AIQueryPreviewCard from '../components/sql-studio/AIQueryPreviewCard'
import NaturalLanguageSQLBar from '../components/sql-studio/NaturalLanguageSQLBar'
import QueryExplanationModal from '../components/sql-studio/QueryExplanationModal'
import QueryHistoryPanel from '../components/sql-studio/QueryHistoryPanel'
import SQLCommandLibraryModal from '../components/sql-studio/SQLCommandLibraryModal'
import SQLEditorWithAutocomplete from '../components/sql-studio/SQLEditorWithAutocomplete'
import {
  sqlStudioService,
  type QueryHistoryRecord,
  type SQLExplanationResponse,
  type SQLGenerationResponse,
  type SQLResult,
  type SQLSuggestionItem,
  type SQLValidationResponse,
  type SchemaColumn,
} from '../services/sqlStudioService'

export default function SQLStudioPage() {
  const { id } = useParams()
  const datasetId = Number(id)

  const [schemaColumns, setSchemaColumns] = useState<SchemaColumn[]>([])
  const [totalRows, setTotalRows] = useState(0)
  const [query, setQuery] = useState('SELECT * FROM dataset LIMIT 25;')
  const [result, setResult] = useState<SQLResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

  // 1. Natural Language to SQL State
  const [nlPrompt, setNlPrompt] = useState('')
  const [nlLoading, setNlLoading] = useState(false)
  const [autoSuggest, setAutoSuggest] = useState(false)
  const [aiPreview, setAiPreview] = useState<SQLGenerationResponse | null>(null)
  const [schemaSuggestions, setSchemaSuggestions] = useState<SQLSuggestionItem[]>([])

  // 2. Query Explanation & Validation State
  const [explanationData, setExplanationData] = useState<SQLExplanationResponse | null>(null)
  const [explainingQuery, setExplainingQuery] = useState(false)
  const [explanationModalOpen, setExplanationModalOpen] = useState(false)
  const [validationResult, setValidationResult] = useState<SQLValidationResponse | null>(null)
  const [validating, setValidating] = useState(false)

  // 3. Command Library Modal State
  const [commandLibraryOpen, setCommandLibraryOpen] = useState(false)

  // 4. Visualization & View Mode State
  const [viewMode, setViewMode] = useState<'table' | 'chart'>('table')
  const [chartType, setChartType] = useState<'bar' | 'line' | 'scatter'>('bar')
  const [xAxis, setXAxis] = useState('')
  const [yAxis, setYAxis] = useState('')

  // 5. Query History State (Persistent with metadata)
  const [historyRecords, setHistoryRecords] = useState<QueryHistoryRecord[]>(() => {
    try {
      const saved = localStorage.getItem(`analyticx_sql_history_v2_${datasetId}`)
      if (saved) return JSON.parse(saved)
      // fallback legacy format
      const legacy = localStorage.getItem(`analyticx_sql_history_${datasetId}`)
      if (legacy) {
        const parsed: string[] = JSON.parse(legacy)
        return parsed.map((q, idx) => ({
          id: `legacy-${idx}`,
          query: q,
          timestamp: 'Recent',
          status: 'success',
        }))
      }
      return []
    } catch {
      return []
    }
  })

  const saveHistoryRecords = (records: QueryHistoryRecord[]) => {
    setHistoryRecords(records)
    try {
      localStorage.setItem(`analyticx_sql_history_v2_${datasetId}`, JSON.stringify(records))
    } catch {
      // ignore
    }
  }

  // Load Schema and Context-Aware Recommendations
  useEffect(() => {
    if (!datasetId) return

    sqlStudioService
      .getSchema(datasetId)
      .then((res) => {
        setSchemaColumns(res.columns)
        setTotalRows(res.total_rows)

        const numCols = res.columns.filter((c) => c.is_numeric)
        const catCols = res.columns.filter((c) => !c.is_numeric)
        if (catCols.length > 0 && numCols.length > 0) {
          const cat = catCols[0].name
          const num = numCols[0].name
          const defaultQ = `SELECT "${cat}", COUNT(*) as count, ROUND(SUM("${num}"), 2) as total_${num.toLowerCase()}\nFROM dataset\nGROUP BY "${cat}"\nORDER BY total_${num.toLowerCase()} DESC\nLIMIT 20;`
          setQuery(defaultQ)
        }
      })
      .catch((err) => setError(getErrorMessage(err)))

    sqlStudioService
      .getSuggestions(datasetId)
      .then((suggs) => setSchemaSuggestions(suggs))
      .catch(() => {})
  }, [datasetId])

  // Optional Live Debounced Auto-Suggest
  useEffect(() => {
    if (!autoSuggest || !nlPrompt.trim() || nlPrompt.trim().length < 4) return
    const timer = setTimeout(async () => {
      try {
        const res = await sqlStudioService.generateSQL(datasetId, nlPrompt.trim(), true)
        setAiPreview(res)
      } catch {
        // silent fail on background auto-suggest
      }
    }, 600)
    return () => clearTimeout(timer)
  }, [nlPrompt, autoSuggest, datasetId])

  // Generate SQL from Natural Language
  const handleGenerateSQL = async () => {
    if (!nlPrompt.trim()) return
    setNlLoading(true)
    setError('')
    try {
      const res = await sqlStudioService.generateSQL(datasetId, nlPrompt.trim(), false)
      setAiPreview(res)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setNlLoading(false)
    }
  }

  // Insert AI Generated Query
  const handleInsertAIQuery = (sqlText: string, mode: 'append' | 'replace') => {
    if (mode === 'replace') {
      setQuery(sqlText)
    } else {
      setQuery((prev) => (prev.trim() ? `${prev}\n\n${sqlText}` : sqlText))
    }
    setAiPreview(null)
  }

  // Explain Query
  const handleExplainQuery = async (sqlToExplain?: string) => {
    const q = (sqlToExplain || query).trim()
    if (!q) return
    setExplainingQuery(true)
    setError('')
    try {
      const res = await sqlStudioService.explainSQL(datasetId, q)
      setExplanationData(res)
      setExplanationModalOpen(true)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setExplainingQuery(false)
    }
  }

  // Validate Query via SQLite EXPLAIN QUERY PLAN
  const handleValidateQuery = async () => {
    const q = query.trim()
    if (!q) return
    setValidating(true)
    setError('')
    try {
      const res = await sqlStudioService.validateSQL(datasetId, q)
      setValidationResult(res)
      setTimeout(() => setValidationResult(null), 5000)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setValidating(false)
    }
  }

  // Execute SQL Query
  const runQuery = async (sqlText?: string) => {
    const q = (sqlText ?? query).trim()
    if (!q) return
    setLoading(true)
    setError('')
    setValidationResult(null)

    const startTime = Date.now()
    try {
      const res = await sqlStudioService.executeSQL(datasetId, q, 500)
      setResult(res)

      // Auto-assign X and Y axis for chart
      if (res.columns.length >= 2) {
        setXAxis(res.columns[0])
        setYAxis(res.columns[1])
      } else if (res.columns.length === 1) {
        setXAxis(res.columns[0])
        setYAxis(res.columns[0])
      }

      // Add to structured query history
      const newRecord: QueryHistoryRecord = {
        id: `${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
        query: q,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        execution_time_ms: res.execution_time_ms,
        row_count: res.row_count,
        status: 'success',
        is_favorite: false,
      }
      saveHistoryRecords([newRecord, ...historyRecords.filter((h) => h.query !== q)].slice(0, 30))
    } catch (err) {
      const errMsg = getErrorMessage(err)
      setError(errMsg)

      // Record failed execution
      const failRecord: QueryHistoryRecord = {
        id: `${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
        query: q,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        status: 'error',
        error_message: errMsg,
      }
      saveHistoryRecords([failRecord, ...historyRecords.filter((h) => h.query !== q)].slice(0, 30))
    } finally {
      setLoading(false)
    }
  }

  const handleCopySQL = () => {
    navigator.clipboard.writeText(query)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleExportCSV = () => {
    if (!result || !result.rows.length) return
    const headers = result.columns.join(',')
    const rows = result.rows.map((row) =>
      result.columns
        .map((col) => {
          const val = row[col]
          return typeof val === 'string' && val.includes(',') ? `"${val}"` : String(val ?? '')
        })
        .join(',')
    )
    const csvContent = [headers, ...rows].join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `sql_query_result_dataset_${datasetId}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      {/* 1. Breadcrumb Navigation & Top Metadata */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          to={`/datasets/${datasetId}`}
          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-xs text-cyan-300 transition hover:border-cyan-500/50 hover:bg-slate-800"
        >
          <ArrowLeft size={14} />
          Back to Dataset Studio
        </Link>
        <div className="flex items-center gap-2">
          <span className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-0.5 text-xs font-semibold text-cyan-300 flex items-center gap-1">
            <ShieldCheck size={12} />
            Pro Mode · In-Memory SQLite Sandbox
          </span>
          <span className="text-xs text-slate-500 font-mono">Dataset #{datasetId}</span>
        </div>
      </div>

      {/* 2. Header Title */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-100 flex items-center gap-2.5">
          <Code2 size={26} className="text-cyan-400" />
          Interactive SQL Query Studio
        </h1>
        <p className="mt-1 text-xs text-slate-400 max-w-3xl leading-relaxed">
          AI-assisted SQL workspace with schema-grounded natural language synthesis, keyword and column autocomplete, interactive parameter templates, and instant read-only SQLite execution.
        </p>
      </div>

      {/* 3. PRIMARY FEATURE: NATURAL LANGUAGE TO SQL INPUT BAR */}
      <NaturalLanguageSQLBar
        prompt={nlPrompt}
        setPrompt={setNlPrompt}
        onGenerate={handleGenerateSQL}
        loading={nlLoading}
        autoSuggest={autoSuggest}
        setAutoSuggest={setAutoSuggest}
        suggestions={schemaSuggestions}
        onSelectSuggestion={(sugg) => {
          setNlPrompt(sugg.prompt)
          setQuery(sugg.sql)
        }}
        clarifyingQuestions={aiPreview?.clarifying_questions}
      />

      {/* 4. AI-GENERATED QUERY PREVIEW CARD (When Generated) */}
      {aiPreview && (
        <AIQueryPreviewCard
          preview={aiPreview}
          onInsert={handleInsertAIQuery}
          onExplain={(sql) => handleExplainQuery(sql)}
          onClear={() => setAiPreview(null)}
        />
      )}

      {/* 5. Main Grid: Left Drawer (Schema & History) + Right Workspace (Editor & Results) */}
      <div className="grid gap-6 lg:grid-cols-4">
        {/* Left Column: Schema Reference & Query History */}
        <aside className="glass rounded-3xl p-5 lg:col-span-1 space-y-5 max-h-[780px] overflow-y-auto">
          {/* Table Schema Panel */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <Database size={13} className="text-cyan-400" />
                Table Schema
              </h2>
              <span className="text-[10px] text-slate-400 font-mono">
                {schemaColumns.length} cols · {totalRows} rows
              </span>
            </div>

            <p className="text-[11px] text-slate-400 leading-tight">
              Click any column to append it to your query:
            </p>

            <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
              {schemaColumns.map((col) => (
                <button
                  key={col.name}
                  type="button"
                  onClick={() => setQuery((prev) => `${prev} "${col.name}"`)}
                  className="w-full text-left rounded-xl border border-slate-800/80 bg-slate-900/40 p-2 text-xs hover:border-cyan-500/40 hover:bg-slate-900/80 transition group"
                >
                  <div className="flex items-center justify-between font-mono">
                    <span className="font-medium text-slate-200 group-hover:text-cyan-300 truncate">
                      {col.name}
                    </span>
                    <span
                      className={`text-[9px] rounded px-1.5 py-0.5 ${
                        col.is_numeric
                          ? 'bg-cyan-500/10 text-cyan-300'
                          : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {col.type}
                    </span>
                  </div>
                  {col.sample_values.length > 0 && (
                    <p className="mt-0.5 text-[9px] text-slate-500 truncate">
                      ex: {col.sample_values.join(', ')}
                    </p>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Upgraded Query History Panel */}
          <div className="border-t border-slate-800 pt-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5 mb-2.5">
              <History size={13} className="text-cyan-400" />
              Query History & Saved
            </h3>
            <QueryHistoryPanel
              history={historyRecords}
              onSelectQuery={(sql) => setQuery(sql)}
              onToggleFavorite={(id) => {
                const next = historyRecords.map((h) =>
                  h.id === id ? { ...h, is_favorite: !h.is_favorite } : h
                )
                saveHistoryRecords(next)
              }}
              onRenameQuery={(id, name) => {
                const next = historyRecords.map((h) => (h.id === id ? { ...h, name } : h))
                saveHistoryRecords(next)
              }}
              onDeleteQuery={(id) => {
                const next = historyRecords.filter((h) => h.id !== id)
                saveHistoryRecords(next)
              }}
              onClearHistory={() => saveHistoryRecords([])}
            />
          </div>
        </aside>

        {/* Right Columns: SQL Editor Workspace & Results */}
        <section className="glass rounded-3xl p-6 lg:col-span-3 space-y-4 flex flex-col">
          {/* Action Header Deck */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
            {/* Left Quick SQL Actions */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-slate-400">Quick SQL:</span>
              <button
                type="button"
                onClick={() => setQuery('SELECT * FROM dataset LIMIT 25;')}
                className="rounded-xl border border-slate-800 bg-slate-900/80 px-2.5 py-1 text-xs text-slate-300 hover:border-cyan-500/40 hover:text-cyan-200 transition"
              >
                Sample 25
              </button>
              <button
                type="button"
                onClick={() => setQuery('SELECT COUNT(*) as total_records FROM dataset;')}
                className="rounded-xl border border-slate-800 bg-slate-900/80 px-2.5 py-1 text-xs text-slate-300 hover:border-cyan-500/40 hover:text-cyan-200 transition"
              >
                Row Count
              </button>
              <button
                type="button"
                onClick={() => setCommandLibraryOpen(true)}
                className="inline-flex items-center gap-1.5 rounded-xl border border-purple-500/30 bg-purple-500/10 px-3 py-1 text-xs font-semibold text-purple-300 hover:bg-purple-500/20 transition shadow-sm"
              >
                <BookOpen size={13} />
                SQL Command Library
              </button>
            </div>

            {/* Right Execution & Inspection Actions */}
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={handleValidateQuery}
                disabled={validating || !query.trim()}
                title="Validate syntax and schema using SQLite EXPLAIN QUERY PLAN"
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:text-emerald-300 hover:border-emerald-500/40 transition disabled:opacity-50"
              >
                <CheckCircle2 size={13} className={validating ? 'animate-spin' : ''} />
                Validate SQL
              </button>

              <button
                onClick={() => handleExplainQuery()}
                disabled={explainingQuery || !query.trim()}
                title="Explain query logic in plain English"
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:text-purple-300 hover:border-purple-500/40 transition disabled:opacity-50"
              >
                <FileQuestion size={13} />
                Explain
              </button>

              <button
                onClick={handleCopySQL}
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-slate-300 hover:text-slate-100 hover:border-slate-700 transition"
              >
                {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
                {copied ? 'Copied' : 'Copy'}
              </button>

              <button
                onClick={() => runQuery()}
                disabled={loading || !query.trim()}
                className="inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-4 py-1.5 text-xs font-bold text-slate-950 hover:bg-cyan-300 disabled:opacity-50 transition shadow-md shadow-cyan-950/40"
              >
                <Play size={14} className={loading ? 'animate-spin' : ''} />
                {loading ? 'Running...' : 'Execute SQL'}
              </button>
            </div>
          </div>

          {/* Validation Status Notification */}
          {validationResult && (
            <div
              className={`rounded-2xl p-3 text-xs flex items-center justify-between border ${
                validationResult.valid
                  ? 'border-emerald-500/30 bg-emerald-950/20 text-emerald-200'
                  : 'border-red-500/30 bg-red-950/20 text-red-200'
              }`}
            >
              <div className="flex items-center gap-2">
                {validationResult.valid ? (
                  <CheckCircle2 size={15} className="text-emerald-400 shrink-0" />
                ) : (
                  <AlertCircle size={15} className="text-red-400 shrink-0" />
                )}
                <span>
                  {validationResult.valid
                    ? 'SQL statement is valid and safe for read-only sandbox execution.'
                    : `Validation Error: ${validationResult.error}`}
                </span>
              </div>
              <button
                onClick={() => setValidationResult(null)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X size={13} />
              </button>
            </div>
          )}

          {/* UPGRADED SQL EDITOR WITH AUTOCOMPLETE & INTELLISENSE */}
          <SQLEditorWithAutocomplete
            value={query}
            onChange={setQuery}
            schemaColumns={schemaColumns}
            placeholder="SELECT column_name, SUM(metric) FROM dataset GROUP BY 1..."
          />

          {/* Error Notification */}
          {error && (
            <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-3.5 text-xs text-red-200 flex items-start gap-2">
              <AlertCircle size={16} className="text-red-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <span className="font-semibold">Query Execution Failed</span>
                <p className="text-[11px] opacity-90">{error}</p>
              </div>
            </div>
          )}

          {/* Results Area */}
          {result && (
            <div className="space-y-4 pt-2">
              {/* Results Topbar: Table vs Chart Toggle + Stats + CSV Export */}
              <div className="flex flex-wrap items-center justify-between gap-3 text-xs border-b border-slate-800 pb-3">
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1.5 text-slate-200 font-semibold">
                    <TableIcon size={14} className="text-cyan-400" />
                    {result.row_count} rows
                  </span>
                  <span className="flex items-center gap-1 text-slate-400">
                    <Clock size={12} />
                    {result.execution_time_ms} ms
                  </span>
                  {result.truncated && (
                    <span className="text-[10px] text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                      Capped at 500 records
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {/* Table vs Chart Switcher */}
                  <div className="flex items-center rounded-xl border border-slate-800 bg-slate-900/80 p-0.5">
                    <button
                      onClick={() => setViewMode('table')}
                      className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs transition ${
                        viewMode === 'table'
                          ? 'bg-cyan-400 text-slate-950 font-semibold'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <TableIcon size={12} />
                      Data Table
                    </button>
                    <button
                      onClick={() => setViewMode('chart')}
                      className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs transition ${
                        viewMode === 'chart'
                          ? 'bg-cyan-400 text-slate-950 font-semibold'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <BarChart3 size={12} />
                      Plot Chart
                    </button>
                  </div>

                  <button
                    onClick={handleExportCSV}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-xs text-cyan-300 hover:border-cyan-500/50 hover:bg-slate-800 transition"
                  >
                    <Download size={13} />
                    Export CSV
                  </button>
                </div>
              </div>

              {/* View 1: Data Table */}
              {viewMode === 'table' && (
                <div className="max-h-[380px] overflow-auto rounded-2xl border border-slate-800 bg-slate-900/40">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="sticky top-0 bg-slate-900 text-[11px] font-semibold uppercase tracking-wider text-slate-400 border-b border-slate-800">
                      <tr>
                        {result.columns.map((col) => (
                          <th key={col} className="p-3">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {result.rows.map((row, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/30 transition">
                          {result.columns.map((col) => (
                            <td key={col} className="p-3 font-mono text-slate-200">
                              {row[col] !== null && row[col] !== undefined ? (
                                String(row[col])
                              ) : (
                                <span className="text-slate-600">NULL</span>
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* View 2: Interactive Chart Visualization */}
              {viewMode === 'chart' && (
                <div className="space-y-4">
                  {/* Axis & Type controls */}
                  <div className="flex flex-wrap items-center gap-3 p-3 rounded-2xl border border-slate-800 bg-slate-900/60 text-xs">
                    <div className="flex items-center gap-1.5">
                      <span className="text-slate-400">Chart:</span>
                      <select
                        value={chartType}
                        onChange={(e) => setChartType(e.target.value as 'bar' | 'line' | 'scatter')}
                        className="rounded-lg border border-slate-800 bg-slate-900 px-2.5 py-1 text-slate-200"
                      >
                        <option value="bar">Bar Chart</option>
                        <option value="line">Line Chart</option>
                        <option value="scatter">Scatter Plot</option>
                      </select>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <span className="text-slate-400">X-Axis:</span>
                      <select
                        value={xAxis}
                        onChange={(e) => setXAxis(e.target.value)}
                        className="rounded-lg border border-slate-800 bg-slate-900 px-2.5 py-1 text-slate-200"
                      >
                        {result.columns.map((c) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <span className="text-slate-400">Y-Axis:</span>
                      <select
                        value={yAxis}
                        onChange={(e) => setYAxis(e.target.value)}
                        className="rounded-lg border border-slate-800 bg-slate-900 px-2.5 py-1 text-slate-200"
                      >
                        {result.columns.map((c) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {/* Rendered Plotly Chart */}
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 h-[380px] overflow-hidden">
                    {xAxis && yAxis && (
                      <Plot
                        data={[
                          {
                            x: result.rows.map((r) => String(r[xAxis] ?? '')),
                            y: result.rows.map((r) => Number(r[yAxis]) || 0),
                            type: chartType === 'bar' ? 'bar' : 'scatter',
                            mode:
                              chartType === 'line'
                                ? 'lines+markers'
                                : chartType === 'scatter'
                                ? 'markers'
                                : undefined,
                            marker: { color: '#22d3ee' },
                            line: { color: '#22d3ee', width: 2 },
                          },
                        ] as never}
                        layout={
                          {
                            autosize: true,
                            margin: { l: 50, r: 20, t: 30, b: 60 },
                            paper_bgcolor: 'transparent',
                            plot_bgcolor: 'transparent',
                            font: { color: '#94a3b8', size: 11 },
                            xaxis: { title: { text: xAxis }, gridcolor: '#1e293b' },
                            yaxis: { title: { text: yAxis }, gridcolor: '#1e293b' },
                          } as never
                        }
                        useResizeHandler
                        style={{ width: '100%', height: '100%' }}
                      />
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      </div>

      {/* 6. MODAL: SQL Command & Template Library */}
      <SQLCommandLibraryModal
        isOpen={commandLibraryOpen}
        onClose={() => setCommandLibraryOpen(false)}
        onInsert={(sql) => setQuery(sql)}
        schemaColumns={schemaColumns}
      />

      {/* 7. MODAL: Query Explanation */}
      <QueryExplanationModal
        isOpen={explanationModalOpen}
        onClose={() => setExplanationModalOpen(false)}
        explanation={explanationData}
        query={query}
      />
    </div>
  )
}
