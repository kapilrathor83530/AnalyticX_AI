import Plot from 'react-plotly.js'

interface Props {
  data: Record<string, unknown>[]
  mapping: Record<string, unknown>
  appearance?: Record<string, unknown>
  title?: string
}

export default function LineChart({ data, mapping, appearance, title }: Props) {
  const x = mapping.x as string
  const y = mapping.y as string | string[]
  const series = mapping.series as string | undefined
  const isArea = appearance?.fill === 'tozeroy' || appearance?.area === true
  const isStacked = Boolean(appearance?.stacked)

  if (Array.isArray(y)) {
    return (
      <Plot
        data={y.map((metric) => ({
          type: 'scatter',
          mode: 'lines+markers',
          name: metric,
          fill: isArea ? 'tozeroy' : undefined,
          stackgroup: isStacked ? 'one' : undefined,
          x: data.map((row) => row[x]),
          y: data.map((row) => Number(row[metric] ?? row.count ?? 0)),
        })) as never}
        layout={baseLayout(title, appearance)}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler={true}
        config={{ displayModeBar: false, responsive: true }}
      />
    )
  }

  if (series) {
    const seriesValues = Array.from(new Set(data.map((row) => String(row[series]))))
    const xValues = Array.from(new Set(data.map((row) => String(row[x]))))

    const traces = seriesValues.map((seriesValue) => ({
      type: 'scatter',
      mode: 'lines+markers',
      name: seriesValue,
      fill: isArea ? 'tozeroy' : undefined,
      stackgroup: isStacked ? 'one' : undefined,
      x: xValues,
      y: xValues.map((xValue) => {
        const row = data.find((r) => String(r[x]) === xValue && String(r[series]) === seriesValue)
        return row ? Number(row[y] ?? row.count ?? 0) : null
      }),
    }))

    return (
      <Plot
        data={traces as never}
        layout={baseLayout(title, { legend: true, ...appearance })}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler={true}
        config={{ displayModeBar: false, responsive: true }}
      />
    )
  }

  return (
    <Plot
      data={[
        {
          type: 'scatter',
          mode: 'lines+markers',
          fill: isArea ? 'tozeroy' : undefined,
          stackgroup: isStacked ? 'one' : undefined,
          x: data.map((row) => row[x]) as never,
          y: data.map((row) => Number(row[y] ?? row.count ?? 0)) as never,
          line: { color: (appearance?.color as string) || '#22d3ee', shape: appearance?.smooth ? 'spline' : 'linear' },
          marker: { color: (appearance?.color as string) || '#22d3ee' },
        },
      ]}
      layout={baseLayout(title, appearance)}
      style={{ width: '100%', height: '100%' }}
      useResizeHandler={true}
      config={{ displayModeBar: false, responsive: true }}
    />
  )
}

function baseLayout(title?: string, appearance?: Record<string, unknown>) {
  return {
    title: { text: title || '', font: { color: '#cbd5e1' } },
    autosize: true,
    margin: { l: 55, r: 20, t: 40, b: 50 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: '#cbd5e1' },
    showlegend: Boolean(appearance?.legend),
    xaxis: appearance?.xLabel ? { title: { text: String(appearance.xLabel) } } : undefined,
    yaxis: appearance?.yLabel ? { title: { text: String(appearance.yLabel) } } : undefined,
  }
}
