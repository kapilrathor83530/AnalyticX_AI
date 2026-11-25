import Plot from 'react-plotly.js'

interface Props {
  data: Record<string, unknown>[]
  title?: string
  appearance?: Record<string, unknown>
}

export default function Histogram({ data, title, appearance }: Props) {
  const x = data.map((row) => Number(row.bin_start))
  const y = data.map((row) => Number(row.count))

  return (
    <Plot
      data={[{ type: 'bar', x: x as never, y: y as never, marker: { color: (appearance?.color as string) || '#22d3ee' } }]}
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
