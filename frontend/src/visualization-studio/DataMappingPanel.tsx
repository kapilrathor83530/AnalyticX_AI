import type { ChartTypeDefinition } from '../types/chart'

interface Props {
  chart: ChartTypeDefinition
  columns: string[]
  value: Record<string, string | string[]>
  onChange: (next: Record<string, string | string[]>) => void
  aggregation?: string
  onAggregationChange: (value: string) => void
}

const AGGREGATIONS = ['sum', 'mean', 'median', 'min', 'max', 'count', 'nunique']

export default function DataMappingPanel({ chart, columns, value, onChange, aggregation, onAggregationChange }: Props) {
  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-slate-200">Data Mapping</h3>

      {chart.data_roles.map((role) => {
        const mapped = value[role.name]

        if (role.multiple) {
          const selected = Array.isArray(mapped) ? mapped : []
          return (
            <div key={role.name}>
              <label className="mb-1 block text-xs text-slate-400">{role.label}</label>
              <select
                multiple
                className="h-28 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
                value={selected}
                onChange={(event) => {
                  const next = Array.from(event.target.selectedOptions).map((option) => option.value)
                  onChange({ ...value, [role.name]: next })
                }}
              >
                {columns.map((column) => (
                  <option key={column} value={column}>
                    {column}
                  </option>
                ))}
              </select>
            </div>
          )
        }

        return (
          <div key={role.name}>
            <label className="mb-1 block text-xs text-slate-400">
              {role.label} {role.required && <span className="text-cyan-300">*</span>}
            </label>
            <select
              className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
              value={(mapped as string) || ''}
              onChange={(event) => onChange({ ...value, [role.name]: event.target.value })}
            >
              <option value="">Select column</option>
              {columns.map((column) => (
                <option key={column} value={column}>
                  {column}
                </option>
              ))}
            </select>
          </div>
        )
      })}

      {chart.data_roles.some((role) => role.type === 'measure') && (
        <div>
          <label className="mb-1 block text-xs text-slate-400">Aggregation</label>
          <select
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
            value={aggregation || 'sum'}
            onChange={(event) => onAggregationChange(event.target.value)}
          >
            {AGGREGATIONS.map((agg) => (
              <option key={agg} value={agg}>
                {agg}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  )
}
