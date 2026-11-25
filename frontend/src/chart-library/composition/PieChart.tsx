import Plot from 'react-plotly.js'

interface Props {
  data: Record<string, unknown>[]
  mapping: Record<string, unknown>
  appearance?: Record<string, unknown>
  title?: string
  donut?: boolean
}

export default function PieChart({ data, mapping, appearance, title, donut }: Props) {
  const labels = (mapping.labels || mapping.x) as string
  const values = (mapping.values || mapping.y) as string

  return (
    <Plot
      data={[
        {
          type: 'pie',
          labels: data.map((row) => String(row[labels] ?? '')),
          values: data.map((row) => Number(row[values] ?? row.count ?? 0)),
          hole: donut ? 0.5 : 0,
          textinfo: appearance?.labels === false ? 'none' : 'label+percent',
        },
      ]}
      layout={{
        title: { text: title || '', font: { color: '#cbd5e1' } },
        autosize: true,
        margin: { l: 20, r: 20, t: 40, b: 20 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#cbd5e1' },
        showlegend: appearance?.legend !== false,
      }}
      style={{ width: '100%', height: '100%' }}
      useResizeHandler={true}
      config={{ displayModeBar: false, responsive: true }}
    />
  )
}
