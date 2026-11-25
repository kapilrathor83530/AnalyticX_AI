import {
  ArrowLeft,
  BarChart3,
  Brain,
  Code2,
  FileCheck,
  FileSpreadsheet,
  Lightbulb,
  LineChart,
  Presentation,
  Sliders,
  Sparkles,
  Table2,
  TrendingDown,
  TrendingUp,
  Wand2,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client'
import { useAppMode } from '../contexts/ModeContext'
import type { DatasetPreview, DatasetProfile } from '../types'

export default function ExplorerPage() {
  const { id } = useParams()
  const { mode } = useAppMode()

  const [profile, setProfile] = useState<DatasetProfile | null>(null)
  const [preview, setPreview] = useState<DatasetPreview | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return

    api
      .get<DatasetProfile>(`/datasets/${id}/profile`)
      .then((res) => setProfile(res.data))
      .catch((err) => setError(getErrorMessage(err)))

    api
      .get<DatasetPreview>(`/datasets/${id}/preview`, { params: { limit: 50 } })
      .then((res) => setPreview(res.data))
      .catch((err) => setError(getErrorMessage(err)))
  }, [id])

  return (
    <div className="space-y-8">
      {/* Top Breadcrumb Navigation */}
      <div className="flex items-center justify-between">
        <Link
          to="/workspace"
          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-xs text-cyan-300 transition hover:border-cyan-500/50 hover:bg-slate-800"
        >
          <ArrowLeft size={14} />
          Back to Workspace & Datasets
        </Link>
        <span className="text-xs text-slate-400">Dataset #{id}</span>
      </div>

      {error && (
        <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      {/* Dataset Summary Metrics */}
      {profile && (
        <section className="grid gap-4 md:grid-cols-4">
          <Metric label="Total Records" value={profile.row_count} />
          <Metric label="Columns Ingested" value={profile.column_count} />
          <Metric label="Duplicate Rows" value={profile.duplicate_rows} />
          <Metric label="Analyzed Columns" value={profile.columns.length} />
        </section>
      )}

      {/* Three Modes Interactive Launchpad */}
      <section className="glass rounded-3xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Sparkles size={18} className="text-cyan-400" />
              Three Modes Launchpad
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Choose your workflow mode to clean, explore, or synthesize executive business intelligence.
            </p>
          </div>
          <span className="text-xs text-slate-400">
            Current mode: <strong className="text-cyan-300 capitalize">{mode}</strong>
          </span>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {/* Card 1: Basic Mode */}
          <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/10 p-5 space-y-3 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-300 uppercase">
                  Basic Mode
                </span>
                <FileCheck size={16} className="text-emerald-400" />
              </div>
              <h3 className="text-sm font-bold text-slate-100">Data Cleaning & Preprocessing</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Impute nulls, drop duplicates, winsorize outliers, normalize text, rename fields, and download cleaned CSV + quality report.
              </p>
            </div>
            <Link
              to={`/data-prep/${id}`}
              className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-400 py-2 text-xs font-semibold text-slate-950 hover:bg-emerald-300 transition shadow-sm"
            >
              Open Cleaning Studio
            </Link>
          </div>

          {/* Card 2: Pro Mode */}
          <div className="rounded-2xl border border-cyan-500/30 bg-cyan-950/10 p-5 space-y-3 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 text-[10px] font-bold text-cyan-300 uppercase">
                  Pro Mode
                </span>
                <BarChart3 size={16} className="text-cyan-400" />
              </div>
              <h3 className="text-sm font-bold text-slate-100">EDA, Visualizations & SQL</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Build custom charts (bar, line, scatter, box), generate correlation heatmaps, run sandboxed SQL queries, and compose dashboards.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Link
                to={`/studio/${id}`}
                className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-cyan-400 py-2 text-xs font-semibold text-slate-950 hover:bg-cyan-300 transition shadow-sm"
              >
                <LineChart size={12} />
                Visuals
              </Link>
              <Link
                to={`/sql/${id}`}
                className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-cyan-500/40 bg-slate-900 py-2 text-xs font-semibold text-cyan-300 hover:bg-slate-800 transition"
              >
                <Code2 size={12} />
                SQL Studio
              </Link>
            </div>
          </div>

          {/* Card 3: Advanced Mode */}
          <div className="rounded-2xl border border-purple-500/30 bg-purple-950/10 p-5 space-y-3 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="rounded-full border border-purple-500/30 bg-purple-500/10 px-2 py-0.5 text-[10px] font-bold text-purple-300 uppercase">
                  Advanced Mode
                </span>
                <Sparkles size={16} className="text-purple-400" />
              </div>
              <h3 className="text-sm font-bold text-slate-100">Project Insights & Executive BI</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Automated project EDA, proactive business insights, ANOVA hypothesis tests, AI chat, and downloadable PDF / Word / PPTX board decks.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Link
                to={`/insights/${id}`}
                className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-purple-500 py-2 text-xs font-semibold text-white hover:bg-purple-400 transition shadow-sm"
              >
                <Lightbulb size={12} />
                Project Insights
              </Link>
              <Link
                to={`/forecasting/${id}`}
                className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-purple-500/40 bg-slate-900 py-2 text-xs font-semibold text-purple-300 hover:bg-slate-800 transition"
              >
                <TrendingUp size={12} />
                Forecast
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Column Schema Profile Table */}
      {profile && (
        <section className="glass rounded-3xl p-6">
          <h2 className="mb-5 text-xl font-semibold">Column Profile</h2>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead className="text-slate-400">
                <tr className="border-b border-slate-800">
                  <th className="py-3">Column</th>
                  <th className="py-3">Type</th>
                  <th className="py-3">Missing</th>
                  <th className="py-3">Missing %</th>
                  <th className="py-3">Unique</th>
                  <th className="py-3">Samples</th>
                </tr>
              </thead>
              <tbody>
                {profile.columns.map((column) => (
                  <tr key={column.name} className="border-b border-slate-800/60">
                    <td className="py-3 font-medium">{column.name}</td>
                    <td className="py-3">{column.inferred_type}</td>
                    <td className="py-3">{column.missing_count}</td>
                    <td className="py-3">{column.missing_percent}%</td>
                    <td className="py-3">{column.unique_count}</td>
                    <td className="py-3 text-slate-400">
                      {column.sample_values.map(String).join(', ') || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Data Preview Table */}
      {preview && (
        <section className="glass rounded-3xl p-6">
          <div className="mb-5 flex items-center gap-3">
            <Table2 size={20} className="text-cyan-300" />
            <h2 className="text-xl font-semibold">Data Preview</h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead className="text-slate-400">
                <tr className="border-b border-slate-800">
                  {preview.columns.map((column) => (
                    <th key={column} className="py-3 pr-5">
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.map((row, index) => (
                  <tr key={index} className="border-b border-slate-800/60">
                    {preview.columns.map((column) => (
                      <td key={column} className="py-3 pr-5 text-slate-300">
                        {String(row[column] ?? '')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
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
