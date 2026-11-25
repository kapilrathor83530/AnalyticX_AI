import Plot from 'react-plotly.js'

interface Props {
  data: Record<string, unknown>[]
  mapping: Record<string, unknown>
  title?: string
}

export default function SankeyChart({ data, mapping, title }: Props) {
  const source = mapping.source as string
  const target = mapping.target as string
  const value = mapping.value as string

  const nodes = Array.from(new Set([...data.map((r) => String(r[source])), ...data.map((r) => String(r[target]))]))
  const index = Object.fromEntries(nodes.map((n, i) => [n, i]))

  return (
    <Plot
      data={[
        {
          type: 'sankey',
          node: { label: nodes, color: '#22d3ee' },
          link: {
            source: data.map((r) => index[String(r[source])]),
            target: data.map((r) => index[String(r[target])]),
            value: data.map((r) => Number(r[value])),
          },
        },
      ]}
      layout={{
        title: { text: title || '', font: { color: '#cbd5e1' } },
        autosize: true,
        paper_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#cbd5e1' },
      }}
      style={{ width: '100%', height: '100%' }}
      useResizeHandler={true}
      config={{ displayModeBar: false, responsive: true }}
    />
  )
}
