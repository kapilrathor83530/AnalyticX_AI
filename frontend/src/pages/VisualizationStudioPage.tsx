import { ArrowLeft, LayoutDashboard, Plus, Save, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client'
import { dashboardService } from '../services/dashboardService'
import type { ChartConfig, ChartTypeDefinition, ChartValidationResult } from '../types/chart'
import ChartConfigPanel from '../visualization-studio/ChartConfigPanel'
import ChartRenderer from '../visualization-studio/ChartRenderer'

type CanvasChart = ChartConfig & { id: string }

export default function VisualizationStudioPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const datasetId = Number(id)
  const [columns, setColumns] = useState<string[]>([])
  const [charts, setCharts] = useState<ChartTypeDefinition[]>([])
  const [recommendations, setRecommendations] = useState<import('../types/chart').ChartRecommendation[]>([])
  const [selectedChartId, setSelectedChartId] = useState('bar')
  const [dataMapping, setDataMapping] = useState<Record<string, string | string[]>>({})
  const [appearance, setAppearance] = useState<Record<string, unknown>>({ color: '#22d3ee', legend: true, barmode: 'group' })
  const [title, setTitle] = useState('Untitled Chart')
  const [aggregation, setAggregation] = useState('sum')
  const [sortOrder, setSortOrder] = useState<'none' | 'asc' | 'desc'>('none')
  const [limitCount, setLimitCount] = useState<number>(0)
  const [canvas, setCanvas] = useState<CanvasChart[]>([])
  const [validation, setValidation] = useState<ChartValidationResult | null>(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const selectedChart = useMemo(() => charts.find((chart) => chart.id === selectedChartId), [charts, selectedChartId])
  const config: ChartConfig = { chart_type: selectedChartId, title, data_mapping: dataMapping, filters: [], appearance, aggregation }

  useEffect(() => {
    if (!datasetId) return
    Promise.all([
      api.get<{ columns: string[] }>(`/datasets/${datasetId}/preview`, { params: { limit: 1 } }),
      dashboardService.listCharts(),
      dashboardService.recommendCharts(datasetId, undefined, 8).catch(() => []),
    ])
      .then(([preview, chartList, recsRes]) => {
        const recs = Array.isArray(recsRes) ? recsRes : recsRes?.recommendations || []
        setColumns(preview.data.columns)
        setCharts(chartList)
        setRecommendations(recs)
        if (recs.length > 0 && Object.keys(dataMapping).length === 0) {
          const top = recs[0]
          setSelectedChartId(top.chart_type)
          setDataMapping(top.data_mapping)
          setAggregation(top.aggregation || 'sum')
          setTitle(top.title || 'Recommended Chart')
        }
      })
      .catch((err) => setError(getErrorMessage(err)))
  }, [datasetId])

  const [filterCol, setFilterCol] = useState('')
  const [filterOp, setFilterOp] = useState('eq')
  const [filterVal, setFilterVal] = useState('')
  const activeFilters = filterCol && filterVal.trim() !== ''
    ? [{ column: filterCol, op: filterOp, value: filterVal }]
    : []
  const activeSort = sortOrder === 'none'
    ? undefined
    : {
        column: (Array.isArray(dataMapping.y) ? dataMapping.y[0] : dataMapping.y) || (dataMapping.values as string) || 'count',
        ascending: sortOrder === 'asc',
      }
  const activeLimit = limitCount > 0 ? limitCount : undefined

  function resetEditor(chartId = selectedChartId) {
    setSelectedChartId(chartId); setDataMapping({}); setTitle('Untitled Chart'); setAppearance({ color: '#22d3ee', legend: true, barmode: 'group' }); setValidation(null)
    setSortOrder('none'); setLimitCount(0); setFilterCol(''); setFilterVal('')
  }

  async function addToCanvas() {
    setError(''); setValidation(null)
    const fullConfig = { ...config, filters: activeFilters, sort: activeSort, limit: activeLimit }
    try {
      const result = await dashboardService.validateChart(datasetId, fullConfig as unknown as Record<string, unknown>)
      setValidation(result)
      if (!result.valid) return
      setCanvas((current) => [...current, { ...fullConfig, id: crypto.randomUUID(), data_mapping: { ...dataMapping }, appearance: { ...appearance } }])
      resetEditor()
    } catch (err) { setError(getErrorMessage(err)) }
  }

  async function exportCurrentCsv() {
    if (!datasetId) return
    try {
      const resp = await dashboardService.renderChart(datasetId, {
        ...config,
        filters: activeFilters,
        sort: activeSort,
        limit: activeLimit,
      } as unknown as Record<string, unknown>)
      const rows = resp.data || []
      if (!rows.length) return
      const keys = Object.keys(rows[0])
      const csv = [keys.join(','), ...rows.map((r) => keys.map((k) => JSON.stringify(r[k] ?? '')).join(','))].join('\n')
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${(title || selectedChartId).replace(/[^a-z0-9_-]+/gi, '_')}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function saveDashboard() {
    if (!canvas.length) { setError('Add at least one visual to the canvas before saving.'); return }
    setSaving(true); setError('')
    try {
      const dashboard = await dashboardService.create({ dataset_id: datasetId, name: `Business Dashboard ${new Date().toLocaleDateString()}` })
      await Promise.all(canvas.map((chart, index) => dashboardService.addWidget(dashboard.id, {
        chart_type: chart.chart_type, title: chart.title || 'Untitled Chart', config: { appearance: chart.appearance, aggregation: chart.aggregation, filters: chart.filters, sort: chart.sort, limit: chart.limit }, data_mapping: chart.data_mapping,
        position: { x: (index % 2) * 6, y: Math.floor(index / 2) * 4 }, size: { w: 6, h: 4 },
      })))
      navigate(`/dashboard/${dashboard.id}/edit`)
    } catch (err) { setError(getErrorMessage(err)) } finally { setSaving(false) }
  }

  return <div className="space-y-6">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><Link to={datasetId ? `/datasets/${datasetId}` : '/workspace'} className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-xs text-cyan-300 transition hover:border-cyan-500/50 hover:bg-slate-800"><ArrowLeft size={14} /> Back to Dataset Studio</Link><h1 className="mt-3 text-2xl font-semibold">Visualization Studio</h1><p className="text-sm text-slate-400">Build multiple visuals, then save them together as a decision dashboard.</p></div>
      <button onClick={saveDashboard} disabled={saving || !canvas.length} className="inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50"><Save size={16} />{saving ? 'Saving dashboard…' : `Save ${canvas.length} visual${canvas.length === 1 ? '' : 's'} to Dashboard`}</button>
    </div>
    {error && <div className={`rounded-2xl border px-4 py-3 text-sm ${error.startsWith('Dashboard saved') ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200' : 'border-red-500/30 bg-red-500/10 text-red-200'}`}>{error}</div>}
    {validation && !validation.valid && <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{validation.errors.join('; ')}{validation.suggested_alternative ? ` Try "${validation.suggested_alternative}".` : ''}</div>}
    {recommendations.length > 0 && (
      <section className="glass rounded-3xl p-4">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-wider text-cyan-300">Recommended Charts for This Dataset</p>
          <span className="text-xs text-slate-400">{recommendations.length} validated suggestions</span>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {recommendations.map((rec, idx) => (
            <button
              key={`${rec.chart_type}-${idx}`}
              type="button"
              onClick={() => {
                setSelectedChartId(rec.chart_type)
                setDataMapping(rec.data_mapping)
                setAggregation(rec.aggregation || 'sum')
                setTitle(rec.title)
                setValidation(null)
              }}
              className={`rounded-2xl border p-3 text-left transition ${selectedChartId === rec.chart_type && title === rec.title ? 'border-cyan-400/70 bg-cyan-500/10' : 'border-slate-800 bg-slate-900/50 hover:border-slate-700'}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold text-white truncate">{rec.title}</span>
                <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] uppercase text-cyan-300">{rec.chart_type}</span>
              </div>
              <p className="mt-1 line-clamp-2 text-[11px] text-slate-400">{rec.reason}</p>
            </button>
          ))}
        </div>
      </section>
    )}
    <div className="grid gap-6 xl:grid-cols-[330px_1fr]">
      <aside className="glass h-fit space-y-6 rounded-3xl p-5 xl:sticky xl:top-6">
        <div><label className="mb-1 block text-xs text-slate-400">Visual type</label><select className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm" value={selectedChartId} onChange={(event) => resetEditor(event.target.value)}>{charts.map((chart) => <option key={chart.id} value={chart.id}>{chart.name} · {chart.category}</option>)}</select></div>
        {selectedChart && <ChartConfigPanel chart={selectedChart} columns={columns} dataMapping={dataMapping} onDataMappingChange={setDataMapping} appearance={appearance} onAppearanceChange={setAppearance} title={title} onTitleChange={setTitle} aggregation={aggregation} onAggregationChange={setAggregation} />}
        <div className="space-y-3 border-t border-slate-800 pt-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Sort, Top-N &amp; Filter</p>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="mb-1 block text-[11px] text-slate-400">Sort Order</label>
              <select className="w-full rounded-xl border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs" value={sortOrder} onChange={(e) => setSortOrder(e.target.value as 'none' | 'asc' | 'desc')}>
                <option value="none">Default</option>
                <option value="desc">High to Low</option>
                <option value="asc">Low to High</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[11px] text-slate-400">Limit (Top-N)</label>
              <select className="w-full rounded-xl border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs" value={limitCount} onChange={(e) => setLimitCount(Number(e.target.value))}>
                <option value={0}>All</option>
                <option value={5}>Top 5</option>
                <option value={10}>Top 10</option>
                <option value={15}>Top 15</option>
                <option value={25}>Top 25</option>
              </select>
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="block text-[11px] text-slate-400">Quick Filter</label>
            <select className="w-full rounded-xl border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs" value={filterCol} onChange={(e) => setFilterCol(e.target.value)}>
              <option value="">No filter column</option>
              {columns.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            {filterCol ? (
              <div className="grid grid-cols-2 gap-2">
                <select className="rounded-xl border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs" value={filterOp} onChange={(e) => setFilterOp(e.target.value)}>
                  <option value="eq">Equals</option>
                  <option value="neq">Not Equals</option>
                  <option value="contains">Contains</option>
                  <option value="gt">&gt;</option>
                  <option value="lt">&lt;</option>
                </select>
                <input className="rounded-xl border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs" placeholder="Value..." value={filterVal} onChange={(e) => setFilterVal(e.target.value)} />
              </div>
            ) : null}
          </div>
        </div>
        <button onClick={addToCanvas} className="flex w-full items-center justify-center gap-2 rounded-xl bg-cyan-400 px-3 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-300"><Plus size={16} /> Add visual to canvas</button>
      </aside>
      <main className="space-y-6"><section className="glass rounded-3xl p-5"><div className="mb-3 flex items-center justify-between gap-2"><div className="flex items-center gap-2 text-sm font-medium"><LayoutDashboard size={17} className="text-cyan-300" /> Current visual preview</div><button type="button" onClick={exportCurrentCsv} className="rounded-lg border border-slate-700 px-2.5 py-1 text-xs text-slate-300 hover:border-cyan-400 hover:text-cyan-200">Export CSV</button></div><div className="h-[420px] rounded-2xl border border-slate-800 bg-slate-950/40"><ChartRenderer datasetId={datasetId} chartType={selectedChartId} dataMapping={dataMapping} appearance={appearance} title={title} aggregation={aggregation} filters={activeFilters} sort={activeSort} limit={activeLimit} /></div></section>
        <section className="glass rounded-3xl p-5"><div className="mb-4 flex items-center justify-between"><div><h2 className="font-semibold">Dashboard canvas</h2><p className="text-xs text-slate-500">Add visuals here; saved visuals become dashboard widgets.</p></div><span className="rounded-full bg-cyan-400/10 px-3 py-1 text-xs text-cyan-200">{canvas.length} visuals</span></div>{!canvas.length ? <div className="rounded-2xl border border-dashed border-slate-700 p-10 text-center text-sm text-slate-500">Configure the visual on the left, then click “Add visual to canvas”.</div> : <div className="grid gap-4 2xl:grid-cols-2">{canvas.map((chart) => <article key={chart.id} className="relative h-[360px] rounded-2xl border border-slate-800 bg-slate-950/40 p-3"><button aria-label={`Remove ${chart.title}`} onClick={() => setCanvas((current) => current.filter((item) => item.id !== chart.id))} className="absolute right-3 top-3 z-10 rounded-lg border border-red-500/30 bg-slate-950 p-2 text-red-300 hover:bg-red-500/10"><Trash2 size={14} /></button><ChartRenderer datasetId={datasetId} chartType={chart.chart_type} dataMapping={chart.data_mapping} appearance={chart.appearance} title={chart.title} aggregation={chart.aggregation} filters={chart.filters} sort={chart.sort as { column: string; ascending: boolean } | undefined} limit={chart.limit as number | undefined} /></article>)}</div>}</section></main>
    </div>
  </div>
}
