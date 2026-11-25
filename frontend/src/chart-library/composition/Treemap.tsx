import Plot from 'react-plotly.js'

interface Props {
  data: Record<string, unknown>[]
  mapping: Record<string, unknown>
  title?: string
}

export default function Treemap({ data, mapping, title }: Props) {
  const labels = (mapping.labels || mapping.x) as string
  const values = (mapping.values || mapping.y) as string

  return (
    <Plot
      data={[
        {
          type: 'treemap',
          labels: data.map((row) => String(row[labels])),
          parents: data.map(() => ''),
          values: data.map((row) => Number(row[values])),
        },
      ]}
      layout={{
        title: { text: title || '', font: { color: '#cbd5e1' } },
        autosize: true,
        margin: { l: 10, r: 10, t: 40, b: 10 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#cbd5e1' },
      }}
      style={{ width: '100%', height: '100%' }}
      useResizeHandler={true}
      config={{ displayModeBar: false, responsive: true }}
    />
  )
}
