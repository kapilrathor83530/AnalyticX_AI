import { X } from 'lucide-react'
import { useState } from 'react'
import { useDashboardFilters } from './FilterContext'

interface Props {
  columns: string[]
  valuesByColumn: Record<string, (string | number)[]>
}

export default function DashboardFilters({ columns, valuesByColumn }: Props) {
  const { filters, addFilter, removeFilter, clearFilters } = useDashboardFilters()
  const [column, setColumn] = useState(columns[0] || '')

  const options = valuesByColumn[column] || []

  function apply(value: string | number) {
    addFilter({ column, op: 'eq', value })
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <select
          className="rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs"
          value={column}
          onChange={(e) => setColumn(e.target.value)}
        >
          {columns.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>

        <select
          className="rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs"
          defaultValue=""
          onChange={(e) => {
            if (e.target.value !== '') apply(e.target.value)
          }}
        >
          <option value="">Select value…</option>
          {options.slice(0, 200).map((v) => (
            <option key={String(v)} value={String(v)}>
              {String(v)}
            </option>
          ))}
        </select>

        {filters.length > 0 && (
          <button
            onClick={clearFilters}
            className="rounded-lg border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:border-red-400/50 hover:text-red-300"
          >
            Clear all
          </button>
        )}
      </div>

      {filters.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {filters.map((f) => (
            <span
              key={f.column}
              className="inline-flex items-center gap-1 rounded-full border border-cyan-400/30 bg-cyan-400/5 px-2 py-0.5 text-xs text-cyan-200"
            >
              {f.column} = {String(f.value)}
              <button onClick={() => removeFilter(f.column)}>
                <X size={12} />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
