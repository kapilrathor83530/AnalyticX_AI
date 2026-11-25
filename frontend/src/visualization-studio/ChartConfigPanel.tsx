import type { ChartTypeDefinition } from '../types/chart'
import AppearancePanel from './AppearancePanel'
import DataMappingPanel from './DataMappingPanel'

interface Props {
  chart: ChartTypeDefinition
  columns: string[]
  dataMapping: Record<string, string | string[]>
  onDataMappingChange: (next: Record<string, string | string[]>) => void
  appearance: Record<string, unknown>
  onAppearanceChange: (next: Record<string, unknown>) => void
  title: string
  onTitleChange: (value: string) => void
  aggregation?: string
  onAggregationChange: (value: string) => void
}

export default function ChartConfigPanel({
  chart,
  columns,
  dataMapping,
  onDataMappingChange,
  appearance,
  onAppearanceChange,
  title,
  onTitleChange,
  aggregation,
  onAggregationChange,
}: Props) {
  return (
    <div className="space-y-6">
      <DataMappingPanel
        chart={chart}
        columns={columns}
        value={dataMapping}
        onChange={onDataMappingChange}
        aggregation={aggregation}
        onAggregationChange={onAggregationChange}
      />
      <AppearancePanel value={appearance} onChange={onAppearanceChange} title={title} onTitleChange={onTitleChange} />
    </div>
  )
}
