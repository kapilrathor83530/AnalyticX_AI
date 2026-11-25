interface Props {
  value: Record<string, unknown>
  onChange: (next: Record<string, unknown>) => void
  title: string
  onTitleChange: (value: string) => void
}

export default function AppearancePanel({ value, onChange, title, onTitleChange }: Props) {
  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-slate-200">Appearance</h3>

      <div>
        <label className="mb-1 block text-xs text-slate-400">Title</label>
        <input
          className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
          value={title}
          onChange={(event) => onTitleChange(event.target.value)}
        />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="mb-1 block text-xs text-slate-400">X-Axis Label</label>
          <input
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
            placeholder="Auto"
            value={(value.xLabel as string) || ''}
            onChange={(event) => onChange({ ...value, xLabel: event.target.value })}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-400">Y-Axis Label</label>
          <input
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
            placeholder="Auto"
            value={(value.yLabel as string) || ''}
            onChange={(event) => onChange({ ...value, yLabel: event.target.value })}
          />
        </div>
      </div>

      <div>
        <label className="mb-1 block text-xs text-slate-400">Date Granularity</label>
        <select
          className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
          value={(value.date_granularity as string) || ''}
          onChange={(event) => onChange({ ...value, date_granularity: event.target.value || undefined })}
        >
          <option value="">Auto</option>
          <option value="day">Daily</option>
          <option value="week">Weekly</option>
          <option value="month">Monthly</option>
          <option value="quarter">Quarterly</option>
          <option value="year">Yearly</option>
        </select>
      </div>

      <label className="flex items-center gap-2 text-sm text-slate-300">
        <input
          type="checkbox"
          checked={Boolean(value.smooth)}
          onChange={(event) => onChange({ ...value, smooth: event.target.checked })}
        />
        Smooth trend curve
      </label>

      <div>
        <label className="mb-1 block text-xs text-slate-400">Primary Color</label>
        <input
          type="color"
          className="h-10 w-full rounded-xl border border-slate-700 bg-slate-900"
          value={(value.color as string) || '#22d3ee'}
          onChange={(event) => onChange({ ...value, color: event.target.value })}
        />
      </div>

      <label className="flex items-center gap-2 text-sm text-slate-300">
        <input
          type="checkbox"
          checked={Boolean(value.legend)}
          onChange={(event) => onChange({ ...value, legend: event.target.checked })}
        />
        Show legend
      </label>

      <label className="flex items-center gap-2 text-sm text-slate-300">
        <input
          type="checkbox"
          checked={Boolean(value.labels)}
          onChange={(event) => onChange({ ...value, labels: event.target.checked })}
        />
        Show data labels
      </label>
    </div>
  )
}
