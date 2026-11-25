interface Props {
  data: Record<string, unknown>[]
  title?: string
  appearance?: Record<string, unknown>
}

export default function KPICard({ data, title, appearance }: Props) {
  const row = data[0] || {}
  const value = row.value as number | undefined
  const comparison = row.comparison as number | undefined
  const prefix = (appearance?.prefix as string) || ''
  const suffix = (appearance?.suffix as string) || ''
  const decimals = (appearance?.decimals as number) ?? 2

  const formatted = typeof value === 'number' ? value.toFixed(decimals) : '—'
  const delta = value !== undefined && comparison !== undefined ? value - comparison : undefined
  const deltaPct = comparison ? ((value! - comparison) / comparison) * 100 : undefined

  return (
    <div className="flex h-full flex-col justify-center p-6">
      <p className="text-sm text-slate-400">{title || String(row.label ?? '')}</p>
      <p className="mt-2 text-4xl font-semibold text-slate-100">
        {prefix}
        {formatted}
        {suffix}
      </p>
      {delta !== undefined && (
        <p className={`mt-3 text-sm ${delta >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          {delta >= 0 ? '▲' : '▼'} {Math.abs(delta).toFixed(decimals)}
          {deltaPct !== undefined && ` (${deltaPct.toFixed(2)}%)`}
        </p>
      )}
    </div>
  )
}
