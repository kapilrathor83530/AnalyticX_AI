import { useEffect, useState } from 'react'
import { dashboardService } from '../services/dashboardService'
import BarChart from '../chart-library/comparison/BarChart'
import ViolinPlot from '../chart-library/statistical/ViolinPlot'
import GeoMap from '../chart-library/comparison/GeoMap'
import FunnelChart from '../chart-library/composition/FunnelChart'
import PieChart from '../chart-library/composition/PieChart'
import Treemap from '../chart-library/composition/Treemap'
import WaterfallChart from '../chart-library/composition/WaterfallChart'
import GaugeChart from '../chart-library/business/GaugeChart'
import KPICard from '../chart-library/business/KPICard'
import TableVisual from '../chart-library/business/TableVisual'
import BoxPlot from '../chart-library/statistical/BoxPlot'
import Heatmap from '../chart-library/statistical/Heatmap'
import Histogram from '../chart-library/statistical/Histogram'
import ScatterPlot from '../chart-library/statistical/ScatterPlot'
import LineChart from '../chart-library/trend/LineChart'

interface Props {
  datasetId: number
  chartType: string
  dataMapping: Record<string, unknown>
  appearance?: Record<string, unknown>
  title?: string
  aggregation?: string
  filters?: Array<{ column: string; op: string; value: unknown }>
}

export default function ChartRenderer({ datasetId, chartType, dataMapping, appearance, title, aggregation, filters, sort, limit }: Props & { sort?: { column: string; ascending: boolean } | null; limit?: number | null }) {
  const [data, setData] = useState<Record<string, unknown>[]>([])
  const [error, setError] = useState('')
  const [suggestedAlternative, setSuggestedAlternative] = useState<string | null>(null)
  const [warnings, setWarnings] = useState<string[]>([])
  const [metadata, setMetadata] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    let controller: AbortController | undefined

    const hasMapping = Object.values(dataMapping).some((value) => Array.isArray(value) ? value.length > 0 : Boolean(value))
    if (!hasMapping && chartType !== 'correlation_matrix') {
      setData([])
      return () => { cancelled = true }
    }
    const timer = window.setTimeout(async () => {
      controller = new AbortController()
      setLoading(true)
      setError('')
      try {
        const response = await dashboardService.renderChart(datasetId, {
          chart_type: chartType,
          data_mapping: dataMapping,
          aggregation: aggregation || 'sum',
          filters: filters || [],
          sort: sort || undefined,
          limit: limit || undefined,
          appearance: appearance || {},
          title,
        }, controller.signal)
        if (!cancelled) {
          setData(response.data || [])
          setError(response.error || '')
          setSuggestedAlternative(response.suggested_alternative || null)
          setWarnings(response.warnings || [])
          setMetadata(response.metadata || null)
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load chart')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }, 250)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
      controller?.abort()
    }
  }, [datasetId, chartType, JSON.stringify(dataMapping), JSON.stringify(filters), aggregation, JSON.stringify(appearance), JSON.stringify(sort), limit])

  if (error) {
    return (
      <div className="flex h-full min-h-[220px] flex-col items-center justify-center gap-2 rounded-xl border border-rose-500/30 bg-rose-950/20 p-4 text-center text-sm text-red-300">
        <p>{error}</p>
        {suggestedAlternative ? (
          <p className="text-xs text-cyan-300">
            Suggested alternative: <span className="font-semibold">{suggestedAlternative}</span>
          </p>
        ) : null}
      </div>
    )
  }
  if (loading && !data.length) return <div className="p-4 text-sm text-cyan-200">Preparing visual…</div>
  if (!data.length) return <div className="p-4 text-sm text-slate-500">No data to display. Check the data mapping.</div>

  const renderPlot = () => {
    switch (chartType) {
      case 'bar':
      case 'column':
      case 'clustered_bar':
      case 'grouped_bar':
        return <BarChart data={data} mapping={dataMapping} appearance={{ barmode: 'group', ...appearance }} title={title} />

      case 'horizontal_bar':
        return <BarChart data={data} mapping={dataMapping} appearance={{ ...appearance, orientation: 'horizontal' }} title={title} horizontal />

      case 'stacked_bar':
        return <BarChart data={data} mapping={dataMapping} appearance={{ ...appearance, barmode: 'stack' }} title={title} />

      case 'hundred_percent_stacked_bar':
        return <BarChart data={data} mapping={dataMapping} appearance={{ ...appearance, barmode: 'stack', barnorm: 'percent' }} title={title} />

      case 'line':
      case 'time_series':
        return <LineChart data={data} mapping={dataMapping} appearance={appearance} title={title} />

      case 'area':
        return <LineChart data={data} mapping={dataMapping} appearance={{ ...appearance, area: true }} title={title} />

      case 'stacked_area':
        return <LineChart data={data} mapping={dataMapping} appearance={{ ...appearance, area: true, stacked: true }} title={title} />

      case 'forecast':
        return <LineChart data={data} mapping={{ x: 'date', y: 'value' }} appearance={appearance} title={title} />

      case 'pie':
      case 'donut':
        return <PieChart data={data} mapping={dataMapping} appearance={appearance} title={title} donut={chartType === 'donut'} />

      case 'scatter':
      case 'bubble':
        return <ScatterPlot data={data} mapping={dataMapping} appearance={appearance} title={title} />

      case 'histogram':
        return <Histogram data={data} title={title} appearance={appearance} />

      case 'box':
        return <BoxPlot data={data} title={title} appearance={appearance} />

      case 'violin':
        return <ViolinPlot data={data} title={title} appearance={appearance} />

      case 'heatmap':
      case 'correlation_matrix':
        return <Heatmap data={data} title={title} />

      case 'waterfall':
        return <WaterfallChart data={data} mapping={dataMapping} title={title} appearance={appearance} />

      case 'funnel':
        return <FunnelChart data={data} mapping={dataMapping} title={title} />

      case 'treemap':
        return <Treemap data={data} mapping={dataMapping} title={title} />

      case 'geo_map':
        return <GeoMap data={data} title={title} appearance={appearance} />

      case 'gauge':
        return <GaugeChart data={data} title={title} appearance={appearance} />

      case 'kpi':
        return <KPICard data={data} title={title} appearance={appearance} />

      case 'table':
      case 'matrix':
        return <TableVisual data={data} title={title} />

      default:
        return <div className="p-4 text-sm text-slate-500">Chart type "{chartType}" is registered but not yet rendered in the studio.</div>
    }
  }

  const sampled = Boolean(metadata?.sampled)
  const originalRows = (metadata?.total_source_rows ?? metadata?.original_rows) as number | undefined
  if (!warnings.length && !sampled) {
    return renderPlot()
  }

  return (
    <div className="flex h-full w-full flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {sampled ? (
          <span className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-0.5 text-cyan-300">
            Sampled view ({originalRows ? `${originalRows.toLocaleString()} source rows` : 'large dataset'})
          </span>
        ) : null}
        {warnings.map((warning, index) => (
          <span key={index} className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-0.5 text-amber-200">
            {warning}
          </span>
        ))}
      </div>
      <div className="min-h-0 flex-1">{renderPlot()}</div>
    </div>
  )
}
