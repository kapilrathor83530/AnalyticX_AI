import { useEffect, useMemo, useState } from 'react'
import ChartRenderer from '../visualization-studio/ChartRenderer'
import type { Widget } from '../types/dashboard'
import { useDashboardFilters } from './FilterContext'
import VisualFilterPanel from './VisualFilterPanel'
import WidgetToolbar from './WidgetToolbar'
import { getCachedDatasetPreview } from '../services/datasetCache'

interface Props {
  widget: Widget
  datasetId: number
  columns?: string[]
  valuesByColumn?: Record<string, unknown[]>
  onConfigure: (widget: Widget) => void
  onDelete: (widget: Widget) => void
  onDuplicate?: (widget: Widget) => void
  onUpdate?: (widget: Widget, changes: Partial<Widget>) => void
}

export default function WidgetContainer({
  widget,
  datasetId,
  columns = [],
  valuesByColumn,
  onConfigure,
  onDelete,
  onDuplicate = () => undefined,
  onUpdate = () => undefined,
}: Props) {
  const { filters: dashboardFilters } = useDashboardFilters()
  const [filterOpen, setFilterOpen] = useState(false)
  const [internalValues, setInternalValues] = useState<Record<string, unknown[]>>({})

  const visualFilters = (widget.config?.visual_filters as Array<{ column: string; op: string; value: unknown }>) || []

  // If parent provided valuesByColumn, use it directly; otherwise fetch lazily through deduplicated cache
  useEffect(() => {
    if (valuesByColumn && Object.keys(valuesByColumn).length > 0) {
      return
    }
    // Only load if the filter panel is open or about to be opened
    if (!filterOpen) return

    let cancelled = false
    getCachedDatasetPreview(datasetId, 500)
      .then((data) => {
        if (cancelled) return
        const next: Record<string, unknown[]> = {}
        columns.forEach((column) => {
          next[column] = Array.from(
            new Set(data.rows.map((row) => row[column]).filter((val) => val !== null && val !== undefined))
          ).slice(0, 500)
        })
        setInternalValues(next)
      })
      .catch(() => undefined)

    return () => {
      cancelled = true
    }
  }, [datasetId, columns, filterOpen, valuesByColumn])

  const effectiveValues = (valuesByColumn && Object.keys(valuesByColumn).length > 0)
    ? (valuesByColumn as Record<string, unknown[]>)
    : internalValues

  const combinedFilters = useMemo(() => [...dashboardFilters, ...visualFilters], [dashboardFilters, visualFilters])
  const widgetConfig = {
    chart_type: widget.chart_type,
    title: widget.title,
    data_mapping: widget.data_mapping,
    filters: combinedFilters,
    aggregation: (widget.config?.aggregation as string) || 'sum',
    appearance: (widget.config?.appearance as Record<string, unknown>) || {},
  }

  function saveVisualFilters(next: Array<{ column: string; op: string; value: unknown }>) {
    onUpdate(widget, { config: { ...widget.config, visual_filters: next } })
  }

  return (
    <div id={`widget-container-${widget.id}`} className="glass relative flex h-full flex-col overflow-visible rounded-2xl">
      <div className="widget-drag-handle flex cursor-move items-center justify-between border-b border-slate-800 px-4 py-2 text-sm">
        <span className="font-medium text-slate-200">{widget.title}</span>
        <WidgetToolbar
          widget={widget}
          datasetId={datasetId}
          onFilter={() => setFilterOpen((open) => !open)}
          onEdit={() => onConfigure(widget)}
          onDuplicate={() => onDuplicate(widget)}
          onReset={() => saveVisualFilters([])}
          onRemove={() => onDelete(widget)}
        />
      </div>
      {filterOpen && (
        <div className="visual-filter-panel" onPointerDown={(event) => event.stopPropagation()}>
          <VisualFilterPanel
            columns={columns}
            valuesByColumn={effectiveValues as Record<string, (string | number)[]>}
            initial={visualFilters as never}
            onApply={saveVisualFilters}
            onClose={() => setFilterOpen(false)}
          />
        </div>
      )}
      {(dashboardFilters.length > 0 || visualFilters.length > 0) && (
        <div className="flex flex-wrap gap-1 border-b border-slate-800 px-3 py-1 text-[10px] text-cyan-200">
          {dashboardFilters.length > 0 && (
            <span className="rounded bg-cyan-400/10 px-1">Dashboard filters: {dashboardFilters.length}</span>
          )}
          {visualFilters.length > 0 && (
            <span className="rounded bg-amber-400/10 px-1 text-amber-200">Visual filters: {visualFilters.length}</span>
          )}
        </div>
      )}
      <div className="flex-1 overflow-hidden">
        <ChartRenderer
          datasetId={datasetId}
          chartType={widgetConfig.chart_type}
          dataMapping={widgetConfig.data_mapping}
          appearance={widgetConfig.appearance}
          title={widgetConfig.title}
          aggregation={widgetConfig.aggregation}
          filters={widgetConfig.filters}
        />
      </div>
    </div>
  )
}
