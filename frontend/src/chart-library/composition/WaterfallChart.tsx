import Plot from 'react-plotly.js'

interface Props {
  data: Record<string, unknown>[]
  mapping: Record<string, unknown>
  title?: string
  appearance?: Record<string, unknown>
}

export default function WaterfallChart({ data, mapping, title, appearance }: Props) {
  const labels = (mapping.labels || mapping.x) as string
  const values = (mapping.values || mapping.y) as string

  return (
    <Plot
      data={[
        {
          type: 'waterfall',
          x: data.map((row) => String(row[labels])),
          y: data.map((row) => Number(row[values])),
          connector: { line: { color: '#475569' } },
          increasing: { marker: { color: '#22d3ee' } },
          decreasing: { marker: { color: '#f87171' } },
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
