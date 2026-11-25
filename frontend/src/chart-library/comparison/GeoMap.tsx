import Plot from 'react-plotly.js'

interface Props {
  data: Record<string, unknown>[]
  title?: string
  appearance?: Record<string, unknown>
}

const US_STATE_CODES = new Set([
  'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
  'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
  'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY',
])

export default function GeoMap({ data, title }: Props) {
  const locations = data.map((row) => String(row.location ?? ''))
  const values = data.map((row) => Number(row.value ?? 0))
  const isUsaStates = locations.length > 0 && locations.every((loc) => US_STATE_CODES.has(loc.toUpperCase()))

  return (
    <Plot
      data={[
        {
          type: 'choropleth',
          locationmode: isUsaStates ? 'USA-states' : 'country names',
          locations: isUsaStates ? locations.map((l) => l.toUpperCase()) : locations,
          z: values,
          colorscale: 'Blues',
          marker: { line: { color: '#0f172a', width: 0.8 } },
        } as never,
      ]}
      layout={{
        title: { text: title || '', font: { color: '#cbd5e1' } },
        autosize: true,
        margin: { l: 10, r: 10, t: 40, b: 10 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#cbd5e1' },
        geo: {
          scope: isUsaStates ? 'usa' : 'world',
          bgcolor: 'rgba(0,0,0,0)',
          lakecolor: 'rgba(15,23,42,0.8)',
          showframe: false,
        },
      }}
      style={{ width: '100%', height: '100%' }}
      useResizeHandler={true}
      config={{ displayModeBar: false, responsive: true }}
    />
  )
}
