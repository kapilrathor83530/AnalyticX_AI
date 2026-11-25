import Plot from 'react-plotly.js'

interface Props {
  data: Record<string, unknown>[]
  mapping: Record<string, unknown>
  appearance?: Record<string, unknown>
  title?: string
}

export default function ScatterPlot({ data, mapping, appearance, title }: Props) {
  const x = mapping.x as string
  const y = mapping.y as string
  const color = mapping.color as string | undefined
  const sizeCol = mapping.size as string | undefined

  const sizeValues = sizeCol ? data.map((row) => Number(row[sizeCol] ?? 0)).filter((v) => Number.isFinite(v)) : []
  const minSize = sizeValues.length ? Math.min(...sizeValues) : 0
  const maxSize = sizeValues.length ? Math.max(...sizeValues) : 0
  const computeMarkerSize = (row: Record<string, unknown>) => {
    if (!sizeCol) return 8
    const raw = Number(row[sizeCol] ?? 0)
    if (!Number.isFinite(raw) || maxSize <= minSize) return 14
    return 8 + ((raw - minSize) / (maxSize - minSize)) * 28
  }

  return (
    <Plot
      data={[
        {
          type: 'scatter',
          mode: 'markers',
          x: data.map((row) => Number(row[x])) as never,
          y: data.map((row) => Number(row[y])) as never,
          marker: {
            color: color ? (data.map((row) => row[color] as string | number) as never) : (appearance?.color as string) || '#22d3ee',
            size: sizeCol ? (data.map((row) => computeMarkerSize(row)) as never) : 8,
            opacity: sizeCol ? 0.78 : 0.9,
            line: sizeCol ? { width: 1, color: '#0f172a' } : undefined,
          },
        },
      ]}
      layout={{
        title: { text: title || '', font: { color: '#cbd5e1' } },
        autosize: true,
        margin: { l: 50, r: 20, t: 40, b: 50 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#cbd5e1' },
      }}
      style={{ width: '100%', height: '100%' }}
      useResizeHandler={true}
      config={{ displayModeBar: false, responsive: true }}
    />
  )
}
