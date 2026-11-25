import Plot from 'react-plotly.js'

interface Props {
  data: Record<string, unknown>[]
  title?: string
}

export default function Heatmap({ data, title }: Props) {
  const xs = Array.from(new Set(data.map((r) => String(r.x))))
  const ys = Array.from(new Set(data.map((r) => String(r.y))))

  const z = ys.map((y) =>
    xs.map((x) => {
      const found = data.find((r) => String(r.x) === x && String(r.y) === y)
      return found ? Number(found.value) : 0
    }),
  )

  return (
    <Plot
      data={[
        {
          type: 'heatmap',
          x: xs,
          y: ys,
          z: z as never,
          colorscale: 'Blues',
        },
      ]}
      layout={{
        title: { text: title || '', font: { color: '#cbd5e1' } },
        autosize: true,
        margin: { l: 80, r: 20, t: 40, b: 60 },
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
