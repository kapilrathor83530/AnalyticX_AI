import {
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  Database,
  Download,
  FileSpreadsheet,
  FileText,
  Plus,
  RefreshCw,
  Trash2,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client'
import { reportService } from '../services/reportService'
import { simulationService } from '../services/simulationService'
import type { Scenario, ScenarioAdjustment } from '../types/scenario'

export default function ScenarioSimulatorPage() {
  const { id } = useParams()
  const datasetId = Number(id)

  const [columns, setColumns] = useState<string[]>([])
  const [name, setName] = useState('New Scenario')
  const [metricRevenue, setMetricRevenue] = useState('')
  const [metricCost, setMetricCost] = useState('')
  const [elasticity, setElasticity] = useState<string>('')
  const [adjustments, setAdjustments] = useState<ScenarioAdjustment[]>([])
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [downloadMenuOpen, setDownloadMenuOpen] = useState(false)
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState('')

  useEffect(() => {
    if (!datasetId) return

    async function load() {
      try {
        const [preview, existing] = await Promise.all([
          api.get<{ columns: string[] }>(`/datasets/${datasetId}/preview`, { params: { limit: 1 } }),
          simulationService.list(datasetId),
        ])
        setColumns(preview.data.columns)
        setScenarios(existing)
      } catch (err) {
        setError(getErrorMessage(err))
      }
    }

    load()
  }, [datasetId])

  function addAdjustment() {
    setAdjustments((prev) => [...prev, { field: 'revenue', mode: 'percent', value: 5 }])
  }

  function updateAdjustment(index: number, patch: Partial<ScenarioAdjustment>) {
    setAdjustments((prev) => prev.map((a, i) => (i === index ? { ...a, ...patch } : a)))
  }

  function removeAdjustment(index: number) {
    setAdjustments((prev) => prev.filter((_, i) => i !== index))
  }

  async function run() {
    setLoading(true)
    setError('')
    try {
      const metricColumns: Record<string, string> = {}
      if (metricRevenue) metricColumns.revenue = metricRevenue
      if (metricCost) metricColumns.cost = metricCost

      const created = await simulationService.create({
        dataset_id: datasetId,
        name,
        adjustments,
        metric_columns: metricColumns,
        elasticity: elasticity ? Number(elasticity) : undefined,
      })
      setScenarios((prev) => [created, ...prev])
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadScenarioReport = async (format: 'pdf' | 'xlsx' | 'docx' | 'csv' | 'json') => {
    try {
      setDownloadingFormat(format)
      setDownloadMenuOpen(false)
      await reportService.downloadDirect(
        `/reports/scenarios/${datasetId}/download?format=${format}`,
        `Analyticx_Scenario_Simulation_${datasetId}.${format}`
      )
      setSuccessMessage(`Downloaded scenario report as ${format.toUpperCase()} successfully.`)
      setTimeout(() => setSuccessMessage(''), 4000)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setDownloadingFormat(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          to={datasetId ? `/datasets/${datasetId}` : '/workspace'}
          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-xs text-cyan-300 transition hover:border-cyan-500/50 hover:bg-slate-800"
        >
          <ArrowLeft size={14} />
          Back to Dataset Studio
        </Link>
        <div className="flex items-center gap-3">
          {scenarios.length > 0 && (
            <div className="relative">
              <button
                onClick={() => setDownloadMenuOpen(!downloadMenuOpen)}
                disabled={downloadingFormat !== null}
                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-3.5 py-1.5 text-xs font-bold text-white shadow-lg shadow-cyan-500/20 hover:from-cyan-400 hover:to-blue-500 transition disabled:opacity-50"
              >
                {downloadingFormat ? (
                  <RefreshCw size={13} className="animate-spin" />
                ) : (
                  <Download size={13} />
                )}
                <span>
                  {downloadingFormat ? `Generating ${downloadingFormat.toUpperCase()}...` : 'Export Scenario Report'}
                </span>
                <ChevronDown size={11} className={`transition-transform ${downloadMenuOpen ? 'rotate-180' : ''}`} />
              </button>

              {downloadMenuOpen && (
                <div className="absolute right-0 top-full mt-2 z-50 w-60 rounded-2xl border border-slate-700 bg-slate-950 p-2 shadow-2xl backdrop-blur-xl animate-in fade-in zoom-in-95 duration-100">
                  <div className="px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-800 mb-1">
                    Export Scenario Comparison
                  </div>
                  <button
                    onClick={() => handleDownloadScenarioReport('pdf')}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-left text-xs text-slate-200 hover:bg-slate-800/80 transition"
                  >
                    <FileText size={15} className="text-red-400 shrink-0" />
                    <div>
                      <div className="font-semibold">Executive PDF (.pdf)</div>
                      <div className="text-[10px] text-slate-400">Side-by-side variance & sensitivity</div>
                    </div>
                  </button>
                  <button
                    onClick={() => handleDownloadScenarioReport('xlsx')}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-left text-xs text-slate-200 hover:bg-slate-800/80 transition"
                  >
                    <FileSpreadsheet size={15} className="text-emerald-400 shrink-0" />
                    <div>
                      <div className="font-semibold">Excel Workbook (.xlsx)</div>
                      <div className="text-[10px] text-slate-400">Multi-tab baseline & scenarios</div>
                    </div>
                  </button>
                  <button
                    onClick={() => handleDownloadScenarioReport('docx')}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-left text-xs text-slate-200 hover:bg-slate-800/80 transition"
                  >
                    <FileText size={15} className="text-blue-400 shrink-0" />
                    <div>
                      <div className="font-semibold">Word Document (.docx)</div>
                      <div className="text-[10px] text-slate-400">Editable decision brief</div>
                    </div>
                  </button>
                  <button
                    onClick={() => handleDownloadScenarioReport('csv')}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-left text-xs text-slate-200 hover:bg-slate-800/80 transition"
                  >
                    <Database size={15} className="text-cyan-400 shrink-0" />
                    <div>
                      <div className="font-semibold">Tabular CSV (.csv)</div>
                      <div className="text-[10px] text-slate-400">All scenario metrics & adjustments</div>
                    </div>
                  </button>
                  <button
                    onClick={() => handleDownloadScenarioReport('json')}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-left text-xs text-slate-200 hover:bg-slate-800/80 transition"
                  >
                    <FileText size={15} className="text-purple-400 shrink-0" />
                    <div>
                      <div className="font-semibold">Raw Simulation JSON (.json)</div>
                      <div className="text-[10px] text-slate-400">Complete simulation payload</div>
                    </div>
                  </button>
                </div>
              )}
            </div>
          )}
          <span className="text-xs text-slate-400 font-mono">Dataset #{datasetId}</span>
        </div>
      </div>

      {successMessage && (
        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/20 p-3.5 text-xs text-emerald-200 flex items-center gap-2">
          <CheckCircle2 size={15} className="text-emerald-400 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      <div>
        <h1 className="text-2xl font-semibold">What-If Decision Simulator</h1>
        <p className="text-sm text-slate-400">
          Change business assumptions and compare baseline vs scenario. All results use explicit formulas.
        </p>
      </div>

      {error && (
        <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      <div className="glass space-y-4 rounded-3xl p-6">
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs text-slate-400">Scenario Name</label>
            <input
              className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>

          <div>
            <label className="mb-1 block text-xs text-slate-400">Elasticity (optional, e.g. -0.5)</label>
            <input
              className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
              value={elasticity}
              onChange={(event) => setElasticity(event.target.value)}
              placeholder="-0.5"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs text-slate-400">Revenue Column</label>
            <select
              className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
              value={metricRevenue}
              onChange={(event) => setMetricRevenue(event.target.value)}
            >
              <option value="">None</option>
              {columns.map((col) => (
                <option key={col} value={col}>
                  {col}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs text-slate-400">Cost Column</label>
            <select
              className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
              value={metricCost}
              onChange={(event) => setMetricCost(event.target.value)}
            >
              <option value="">None</option>
              {columns.map((col) => (
                <option key={col} value={col}>
                  {col}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-200">Adjustments</h3>
            <button
              onClick={addAdjustment}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-700 px-3 py-1 text-xs text-slate-200 hover:border-cyan-400/50"
            >
              <Plus size={12} />
              Add
            </button>
          </div>

          {adjustments.length === 0 ? (
            <p className="text-xs text-slate-500">No adjustments yet. Add one to define your scenario.</p>
          ) : (
            <div className="space-y-2">
              {adjustments.map((adjustment, index) => (
                <div key={index} className="flex flex-wrap items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/40 p-2">
                  <select
                    className="rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs"
                    value={adjustment.field}
                    onChange={(event) => updateAdjustment(index, { field: event.target.value })}
                  >
                    <option value="revenue">revenue</option>
                    <option value="cost">cost</option>
                    <option value="price">price</option>
                    <option value="quantity">quantity</option>
                  </select>
                  <select
                    className="rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs"
                    value={adjustment.mode}
                    onChange={(event) =>
                      updateAdjustment(index, { mode: event.target.value as 'percent' | 'absolute' })
                    }
                  >
                    <option value="percent">%</option>
                    <option value="absolute">absolute</option>
                  </select>
                  <input
                    type="number"
                    className="w-24 rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs"
                    value={adjustment.value}
                    onChange={(event) => updateAdjustment(index, { value: Number(event.target.value) })}
                  />
                  <button
                    onClick={() => removeAdjustment(index)}
                    className="ml-auto rounded-lg p-1 text-slate-400 hover:text-red-300"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <button
          onClick={run}
          disabled={loading}
          className="rounded-xl bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-300 disabled:opacity-50"
        >
          {loading ? 'Running...' : 'Run Scenario'}
        </button>
      </div>

      {scenarios.length > 0 && (
        <div className="glass space-y-4 rounded-3xl p-6">
          <h2 className="text-lg font-semibold">Scenario Comparison</h2>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[800px] text-left text-sm">
              <thead className="text-slate-400">
                <tr className="border-b border-slate-800">
                  <th className="py-3">Scenario</th>
                  <th className="py-3">Revenue</th>
                  <th className="py-3">Cost</th>
                  <th className="py-3">Profit</th>
                  <th className="py-3">Margin %</th>
                </tr>
              </thead>
              <tbody>
                {scenarios.map((scenario) => {
                  const r = scenario.results?.scenario || {}
                  return (
                    <tr key={scenario.id} className="border-b border-slate-800/60">
                      <td className="py-3 font-medium">{scenario.name}</td>
                      <td className="py-3">{r.revenue?.toFixed(2) ?? '—'}</td>
                      <td className="py-3">{r.cost?.toFixed(2) ?? '—'}</td>
                      <td className="py-3">{r.profit?.toFixed(2) ?? '—'}</td>
                      <td className="py-3">{r.margin_percent?.toFixed(2) ?? '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {scenarios[0]?.results?.differences && (
            <div>
              <h3 className="mb-2 text-sm font-semibold text-slate-200">Deltas (latest scenario)</h3>
              <ul className="space-y-1 text-xs text-slate-300">
                {Object.entries(scenarios[0].results.differences).map(([key, diff]) => (
                  <li key={key} className="rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2">
                    <span className="text-slate-400">{key}:</span> {diff.diff.toFixed(2)}{' '}
                    {diff.diff_percent !== null && `(${diff.diff_percent.toFixed(2)}%)`}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
