import Plot from 'react-plotly.js'

interface Props {
  data: Record<string, unknown>[]
  title?: string
  appearance?: Record<string, unknown>
}

export default function GaugeChart({ data, title, appearance }: Props) {
  const value = Number(data[0]?.value ?? 0)
  const min = (appearance?.min as number) ?? 0
  const max = (appearance?.max as number) ?? Math.max(value * 1.5, 100)

  return (
    <Plot
      data={[
        {
          type: 'indicator',
          mode: 'gauge+number',
          value: value,
          gauge: {
            axis: { range: [min, max], tickcolor: '#cbd5e1' },
            bar: { color: (appearance?.color as string) || '#22d3ee' },
            bgcolor: 'rgba(0,0,0,0)',
          },
        },
      ]}
      layout={{
        title: { text: title || '', font: { color: '#cbd5e1' } },
        autosize: true,
        margin: { l: 20, r: 20, t: 40, b: 20 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#cbd5e1' },
      }}
      style={{ width: '100%', height: '100%' }}
      useResizeHandler={true}
      config={{ displayModeBar: false, responsive: true }}
    />
  )
}
