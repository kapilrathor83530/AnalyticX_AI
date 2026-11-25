import Plot from 'react-plotly.js'

interface Props {
  data: Record<string, unknown>[]
  title?: string
  appearance?: Record<string, unknown>
}

export default function ViolinPlot({ data, title, appearance }: Props) {
  const color = (appearance?.color as string) || '#22d3ee'
  return (
    <Plot
      data={
        data.map((row) => ({
          type: 'violin',
          name: String(row.group),
          y: row.values as never,
          box: { visible: true },
          meanline: { visible: true },
          line: { color },
          fillcolor: `${color}33`,
        })) as never
      }
      layout={{
        title: { text: title || '', font: { color: '#cbd5e1' } },
        autosize: true,
        margin: { l: 50, r: 20, t: 40, b: 50 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#cbd5e1' },
        showlegend: Boolean(appearance?.legend),
      }}
      style={{ width: '100%', height: '100%' }}
      useResizeHandler={true}
      config={{ displayModeBar: false, responsive: true }}
    />
  )
}
