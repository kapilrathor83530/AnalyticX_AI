import { Archive, ArrowLeft, Download, FileSpreadsheet, FileText, MessageSquare, Plus, Save } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { Layout } from 'react-grid-layout'
import { Link, useParams } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client'
import DashboardGrid from '../dashboard/DashboardGrid'
import DashboardChatPanel from '../dashboard/DashboardChatPanel'
import DashboardFilters from '../dashboard/DashboardFilters'
import { DashboardFilterProvider } from '../dashboard/FilterContext'
import WidgetCommandBar from '../dashboard/WidgetCommandBar'
import { useDashboardHistory } from '../dashboard/useDashboardHistory'
import { dashboardService } from '../services/dashboardService'
import { reportService } from '../services/reportService'
import { useLiveApplicationContext } from '../contexts/LiveApplicationContext'
import type { ChartTypeDefinition } from '../types/chart'
import ChartConfigPanel from '../visualization-studio/ChartConfigPanel'
import type { Dashboard, Widget } from '../types/dashboard'

export default function DashboardEditorPage() {
  const { id } = useParams()
  const dashboardId = Number(id)

  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [charts, setCharts] = useState<ChartTypeDefinition[]>([])
  const [columns, setColumns] = useState<string[]>([])
  const [error, setError] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [newChartType, setNewChartType] = useState('bar')
  const [newTitle, setNewTitle] = useState('New Chart')
  const [valuesByColumn, setValuesByColumn] = useState<Record<string, (string | number)[]>>({})
  const [editing, setEditing] = useState<Widget | null>(null)
  const [editType, setEditType] = useState('bar')
  const [editTitle, setEditTitle] = useState('')
  const [editMapping, setEditMapping] = useState<Record<string, string | string[]>>({})
  const [editAppearance, setEditAppearance] = useState<Record<string, unknown>>({})
  const [editAggregation, setEditAggregation] = useState('sum')
  const [chatOpen, setChatOpen] = useState(true)
  const [saveState, setSaveState] = useState<'saved' | 'saving' | 'error'>('saved')
  const [exportOpen, setExportOpen] = useState(false)

  const { setActiveDashboard, setActiveDataset } = useLiveApplicationContext()

  const { widgets, set: setWidgets, undo, redo, canUndo, canRedo } = useDashboardHistory([])

  // Notify react-grid-layout and charts to recalculate sizes whenever chat side panel opens or closes
  useEffect(() => {
    window.dispatchEvent(new Event('resize'))
    const t1 = setTimeout(() => window.dispatchEvent(new Event('resize')), 100)
    const t2 = setTimeout(() => window.dispatchEvent(new Event('resize')), 320)
    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
    }
  }, [chatOpen])

  useEffect(() => {
    if (!dashboardId) return

    async function load() {
      try {
        const dashboardData = await dashboardService.get(dashboardId)
        setDashboard(dashboardData)
        const [widgetList, chartList, preview] = await Promise.all([
          dashboardService.listWidgets(dashboardId),
          dashboardService.listCharts(),
          api.get<{ columns: string[]; rows: Record<string, unknown>[] }>(`/datasets/${dashboardData.dataset_id}/preview`, { params: { limit: 500 } }),
        ])
        setWidgets(widgetList)
        setCharts(chartList)
        setColumns(preview.data.columns)
        const values: Record<string, (string | number)[]> = {}
        Object.keys(preview.data.rows[0] || {}).forEach((column) => {
          values[column] = Array.from(new Set(preview.data.rows.map((row) => row[column]).filter((value): value is string | number => typeof value === 'string' || typeof value === 'number'))) as (string | number)[]
        })
        setValuesByColumn(values)
        setActiveDashboard({
          dashboardId: dashboardData.id,
          dashboardName: dashboardData.name,
          widgetsCount: widgetList.length,
        })
        setActiveDataset({
          datasetId: dashboardData.dataset_id,
        })
      } catch (err) {
        setError(getErrorMessage(err))
      }
    }

    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dashboardId])

  // Update active widget in context when editing changes
  useEffect(() => {
    if (editing) {
      setActiveDashboard({
        selectedWidgetId: editing.id,
        selectedChartType: editing.chart_type,
        selectedChartTitle: editing.title,
      })
    }
  }, [editing, setActiveDashboard])

  async function handleLayoutChange(layout: Layout[]) {
    if (!dashboard) return
    const updates = widgets.map((widget) => {
      const item = layout.find((entry) => entry.i === String(widget.id))
      if (!item) return null
      return dashboardService.updateWidget(dashboard.id, widget.id, {
        position: { x: item.x, y: item.y },
        size: { w: item.w, h: item.h },
      })
    })

    try {
      setSaveState('saving')
      const updated = await Promise.all(updates.filter(Boolean) as Promise<Widget>[])
      const merged = widgets.map((w) => updated.find((u) => u.id === w.id) || w)
      setWidgets(merged)
      const saved = await dashboardService.saveLayout(dashboard.id, { ...dashboard.layout_config, cols: 12, rowHeight: 60 })
      setDashboard(saved)
      setSaveState('saved')
    } catch (err) {
      setError(getErrorMessage(err)); setSaveState('error')
    }
  }

  async function addWidget() {
    if (!dashboard) return
    try {
      const widget = await dashboardService.addWidget(dashboard.id, {
        chart_type: newChartType,
        title: newTitle,
        config: { appearance: { color: '#22d3ee', legend: true }, aggregation: 'sum' },
        data_mapping: {},
        position: { x: 0, y: Infinity as unknown as number },
        size: { w: 6, h: 4 },
      })
      setWidgets([...widgets, widget])
      setShowAdd(false)
      setNewTitle('New Chart')
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function deleteWidget(widget: Widget) {
    if (!dashboard) return
    try {
      await dashboardService.removeWidget(dashboard.id, widget.id)
      setWidgets(widgets.filter((w) => w.id !== widget.id))
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function updateWidget(widget: Widget, changes: Partial<Widget>) {
    if (!dashboard) return
    try {
      setSaveState('saving')
      const updated = await dashboardService.updateWidget(dashboard.id, widget.id, changes)
      setWidgets(widgets.map((item) => item.id === widget.id ? updated : item))
      setSaveState('saved')
    } catch (err) { setError(getErrorMessage(err)); setSaveState('error') }
  }

  async function duplicateWidget(widget: Widget) {
    if (!dashboard) return
    try {
      const duplicate = await dashboardService.addWidget(dashboard.id, {
        chart_type: widget.chart_type, title: `${widget.title} (copy)`, config: widget.config, data_mapping: widget.data_mapping,
        position: { x: ((widget.position?.x || 0) + 1) % 6, y: (widget.position?.y || 0) + 1 }, size: widget.size,
      })
      setWidgets([...widgets, duplicate])
    } catch (err) { setError(getErrorMessage(err)) }
  }

  async function configureWidget(widget: Widget) {
    setEditing(widget); setEditType(widget.chart_type); setEditTitle(widget.title); setEditMapping(widget.data_mapping as Record<string, string | string[]>); setEditAppearance((widget.config?.appearance as Record<string, unknown>) || { color: '#22d3ee', legend: true }); setEditAggregation((widget.config?.aggregation as string) || 'sum')
  }

  async function saveEditedWidget() {
    if (!editing || !dashboard) return
    try {
      const updated = await dashboardService.updateWidget(dashboard.id, editing.id, { chart_type: editType, title: editTitle, data_mapping: editMapping, config: { ...editing.config, appearance: editAppearance, aggregation: editAggregation } })
      setWidgets(widgets.map((widget) => widget.id === editing.id ? updated : widget)); setEditing(null)
    } catch (err) { setError(getErrorMessage(err)) }
  }

  async function saveDashboardFilters(filters: unknown) {
    if (!dashboard) return
    try {
      const saved = await dashboardService.saveLayout(dashboard.id, { ...dashboard.layout_config, dashboard_filters: filters })
      setDashboard(saved)
    } catch (err) { setError(getErrorMessage(err)) }
  }

  if (!dashboard) return <div className="text-slate-400">Loading dashboard...</div>

  return (
    <DashboardFilterProvider initialFilters={(dashboard.layout_config?.dashboard_filters as never) || []} onChange={saveDashboardFilters}>
    <div className={`transition-all duration-300 space-y-6 ${chatOpen ? 'sm:mr-[390px] xl:mr-[430px]' : 'mr-0'}`}>
      <div className="flex items-center justify-between">
        <Link
          to="/dashboards"
          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-xs text-cyan-300 transition hover:border-cyan-500/50 hover:bg-slate-800"
        >
          <ArrowLeft size={14} />
          Back to Dashboards
        </Link>
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center gap-1 text-xs ${saveState === 'error' ? 'text-red-300' : saveState === 'saving' ? 'text-amber-200' : 'text-emerald-300'}`}>
            <Save size={14} />
            {saveState === 'saving' ? 'Saving…' : saveState === 'error' ? 'Save failed' : 'All changes saved'}
          </span>
          <button
            onClick={() => setChatOpen((open) => !open)}
            className={`inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm transition ${
              chatOpen
                ? 'border-cyan-400 bg-cyan-400/10 text-cyan-200 shadow-sm shadow-cyan-950'
                : 'border-slate-700 hover:border-cyan-400 text-slate-300'
            }`}
          >
            <MessageSquare size={16} />
            {chatOpen ? 'Close AI Chat' : 'AI Chat'}
          </button>
          {/* Export Dashboard Dropdown */}
          <div className="relative">
            <button
              onClick={() => setExportOpen(!exportOpen)}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800/80 px-3.5 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-700 transition"
              title="Download dashboard report or data"
            >
              <Download size={15} />
              Export
            </button>

            {exportOpen && (
              <div className="absolute right-0 top-full mt-2 z-50 w-60 rounded-2xl border border-slate-700 bg-slate-900/95 p-2 shadow-2xl backdrop-blur-xl space-y-1">
                <button
                  onClick={async () => {
                    setExportOpen(false)
                    await reportService.downloadDirect(
                      `/reports/dashboard/${dashboard.dataset_id}/download?format=xlsx`,
                      `${dashboard.name}_Data.xlsx`
                    )
                  }}
                  className="w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-slate-200 hover:bg-slate-800 transition"
                >
                  <FileSpreadsheet size={14} className="text-emerald-400" />
                  <div>
                    <p className="font-semibold">Excel Workbook (.xlsx)</p>
                    <p className="text-[10px] text-slate-400">Sheet per widget data table</p>
                  </div>
                </button>

                <button
                  onClick={async () => {
                    setExportOpen(false)
                    await reportService.downloadDirect(
                      `/reports/dashboard/${dashboard.dataset_id}/download?format=pdf`,
                      `${dashboard.name}_Report.pdf`
                    )
                  }}
                  className="w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-slate-200 hover:bg-slate-800 transition"
                >
                  <FileText size={14} className="text-red-400" />
                  <div>
                    <p className="font-semibold">Dashboard Report (PDF)</p>
                    <p className="text-[10px] text-slate-400">Formatted summary & audit</p>
                  </div>
                </button>

                <button
                  onClick={async () => {
                    setExportOpen(false)
                    await reportService.exportPackage({
                      dataset_id: dashboard.dataset_id,
                      selected_categories: ['dashboard', 'statistical'],
                    })
                  }}
                  className="w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-slate-200 hover:bg-slate-800 transition border-t border-slate-800 mt-1 pt-1.5"
                >
                  <Archive size={14} className="text-indigo-400" />
                  <div>
                    <p className="font-semibold">Full Project Package (ZIP)</p>
                    <p className="text-[10px] text-slate-400">All data tables & stats</p>
                  </div>
                </button>
              </div>
            )}
          </div>

          <button
            onClick={() => setShowAdd((s) => !s)}
            className="inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition"
          >
            <Plus size={16} />
            Add Chart
          </button>
        </div>
      </div>

      <div>
        <h1 className="text-2xl font-semibold">{dashboard.name}</h1>
        <p className="text-sm text-slate-400">
          Dataset #{dashboard.dataset_id} · {widgets.length} widgets
        </p>
      </div>

      <WidgetCommandBar
        dashboardId={dashboard.id}
        datasetId={dashboard.dataset_id}
        widgets={widgets}
        onWidgetsChange={setWidgets}
        onUndo={undo}
        onRedo={redo}
        canUndo={canUndo}
        canRedo={canRedo}
      />

      <section className="glass rounded-2xl p-4">
        <div className="mb-2 text-sm font-medium text-slate-200">Dashboard-level filters</div>
        <p className="mb-3 text-xs text-slate-500">These filters apply to every visual. Visual-level filters remain independent.</p>
        <DashboardFilters columns={columns} valuesByColumn={valuesByColumn} />
      </section>

      {error && (
        <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      {showAdd && (
        <div className="glass flex flex-wrap items-end gap-4 rounded-2xl p-4">
          <div>
            <label className="mb-1 block text-xs text-slate-400">Title</label>
            <input
              className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
              value={newTitle}
              onChange={(event) => setNewTitle(event.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-400">Chart Type</label>
            <select
              className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
              value={newChartType}
              onChange={(event) => setNewChartType(event.target.value)}
            >
              {charts.map((chart) => (
                <option key={chart.id} value={chart.id}>
                  {chart.name}
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={addWidget}
            className="rounded-xl bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-300"
          >
            Add
          </button>
        </div>
      )}

      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 p-4">
          <section className="glass max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-3xl p-6">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold">Edit visual</h2>
                <p className="text-xs text-slate-400">Change type, columns, aggregation, title and appearance.</p>
              </div>
              <button onClick={() => setEditing(null)} className="rounded-lg border border-slate-700 px-3 py-1 text-sm">Cancel</button>
            </div>
            <label className="mb-1 block text-xs text-slate-400">Chart type</label>
            <select
              className="mb-5 w-full rounded-xl border border-slate-700 bg-slate-900 p-2 text-sm"
              value={editType}
              onChange={(event) => { setEditType(event.target.value); setEditMapping({}) }}
            >
              {charts.map((chart) => <option key={chart.id} value={chart.id}>{chart.name}</option>)}
            </select>
            {charts.find((chart) => chart.id === editType) && (
              <ChartConfigPanel
                chart={charts.find((chart) => chart.id === editType)!}
                columns={columns}
                dataMapping={editMapping}
                onDataMappingChange={setEditMapping}
                appearance={editAppearance}
                onAppearanceChange={setEditAppearance}
                title={editTitle}
                onTitleChange={setEditTitle}
                aggregation={editAggregation}
                onAggregationChange={setEditAggregation}
              />
            )}
            <div className="mt-6 flex justify-end gap-3">
              <button onClick={() => setEditing(null)} className="rounded-xl border border-slate-700 px-4 py-2 text-sm">Cancel</button>
              <button onClick={saveEditedWidget} className="rounded-xl bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950">Save visual</button>
            </div>
          </section>
        </div>
      )}

      {widgets.length === 0 ? (
        <div className="glass rounded-3xl p-10 text-center text-sm text-slate-400">
          No widgets yet. Click "Add Chart" or use the command bar.
        </div>
      ) : (
        <DashboardGrid
          widgets={widgets}
          datasetId={dashboard.dataset_id}
          columns={columns}
          valuesByColumn={valuesByColumn}
          onLayoutChange={handleLayoutChange}
          onConfigure={configureWidget}
          onDelete={deleteWidget}
          onDuplicate={duplicateWidget}
          onUpdate={updateWidget}
        />
      )}

      <p className="text-xs text-slate-500">Available columns: {columns.join(', ') || 'loading...'}</p>
    </div>
    {chatOpen && <DashboardChatPanel dashboardId={dashboard.id} onClose={() => setChatOpen(false)} />}
    </DashboardFilterProvider>
  )
}
