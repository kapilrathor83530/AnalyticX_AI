import Plot from 'react-plotly.js'

interface Props {
  data: Record<string, unknown>[]
  mapping: Record<string, unknown>
  appearance?: Record<string, unknown>
  title?: string
  horizontal?: boolean
}

export default function BarChart({ data, mapping, appearance, title, horizontal }: Props) {
  const x = mapping.x as string
  const y = mapping.y as string | string[]
  const series = mapping.series as string | undefined
  const isHorizontal = Boolean(horizontal || appearance?.orientation === 'horizontal')
  const showLabels = Boolean(appearance?.labels)

  if (Array.isArray(y)) {
    return (
      <Plot
        data={y.map((metric) => {
          const cats = data.map((row) => row[x])
          const vals = data.map((row) => Number(row[metric] ?? row.count ?? 0))
          return {
            type: 'bar',
            name: metric,
            orientation: isHorizontal ? 'h' : 'v',
            x: isHorizontal ? vals : cats,
            y: isHorizontal ? cats : vals,
            text: showLabels ? vals.map((v) => String(v)) : undefined,
            textposition: showLabels ? 'auto' : undefined,
          }
        }) as never}
        layout={baseLayout(title, appearance, isHorizontal)}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler={true}
        config={{ displayModeBar: false, responsive: true }}
      />
    )
  }

  if (series) {
    const seriesValues = Array.from(new Set(data.map((row) => String(row[series]))))
    const xValues = Array.from(new Set(data.map((row) => String(row[x]))))

    const traces = seriesValues.map((seriesValue) => {
      const vals = xValues.map((xValue) => {
        const row = data.find((r) => String(r[x]) === xValue && String(r[series]) === seriesValue)
        return row ? Number(row[y] ?? row.count ?? 0) : 0
      })
      return {
        type: 'bar',
        name: seriesValue,
        orientation: isHorizontal ? 'h' : 'v',
        x: isHorizontal ? vals : xValues,
        y: isHorizontal ? xValues : vals,
        text: showLabels ? vals.map((v) => String(v)) : undefined,
        textposition: showLabels ? 'auto' : undefined,
      }
    })

    return (
      <Plot
        data={traces as never}
        layout={baseLayout(title, { legend: true, ...appearance }, isHorizontal)}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler={true}
        config={{ displayModeBar: false, responsive: true }}
      />
    )
  }

  const cats = data.map((row) => row[x])
  const vals = data.map((row) => Number(row[y] ?? row.count ?? 0))

  return (
    <Plot
      data={[
        {
          type: 'bar',
          orientation: isHorizontal ? 'h' : 'v',
          x: (isHorizontal ? vals : cats) as never,
          y: (isHorizontal ? cats : vals) as never,
          text: showLabels ? (vals.map((v) => String(v)) as never) : undefined,
          textposition: showLabels ? 'auto' : undefined,
          marker: { color: (appearance?.color as string) || '#22d3ee' },
        },
      ]}
      layout={baseLayout(title, appearance, isHorizontal)}
      style={{ width: '100%', height: '100%' }}
      useResizeHandler={true}
      config={{ displayModeBar: false, responsive: true }}
    />
  )
}

function baseLayout(title?: string, appearance?: Record<string, unknown>, isHorizontal?: boolean) {
  return {
    title: { text: title || '', font: { color: '#cbd5e1' } },
    autosize: true,
    margin: { l: isHorizontal ? 130 : 55, r: 20, t: 40, b: 50 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: '#cbd5e1' },
    showlegend: Boolean(appearance?.legend),
    barmode: ((appearance?.barmode as 'group' | 'stack' | 'relative' | 'overlay') || 'group'),
    barnorm: appearance?.barnorm === 'percent' ? ('percent' as const) : undefined,
    xaxis: appearance?.xLabel ? { title: { text: String(appearance.xLabel) } } : undefined,
    yaxis: appearance?.yLabel ? { title: { text: String(appearance.yLabel) } } : undefined,
  }
}
