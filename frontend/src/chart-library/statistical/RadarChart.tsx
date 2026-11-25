import Plot from 'react-plotly.js'

interface Props {
  data: Record<string, unknown>[]
  mapping: Record<string, unknown>
  title?: string
}

export default function RadarChart({ data, mapping, title }: Props) {
  const labels = mapping.labels as string
  const values = mapping.values as string

  return (
    <Plot
      data={[
        {
          type: 'scatterpolar',
          r: data.map((r) => Number(r[values])),
          theta: data.map((r) => String(r[labels])),
          fill: 'toself',
          line: { color: '#22d3ee' },
        },
      ]}
      layout={{
        title: { text: title || '', font: { color: '#cbd5e1' } },
        autosize: true,
        polar: { bgcolor: 'rgba(0,0,0,0)' },
        paper_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#cbd5e1' },
      }}
      style={{ width: '100%', height: '100%' }}
      useResizeHandler={true}
      config={{ displayModeBar: false, responsive: true }}
    />
  )
}
