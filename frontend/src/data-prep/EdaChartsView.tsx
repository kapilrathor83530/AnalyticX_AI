import Plot from 'react-plotly.js'
import type { EdaReport } from '../types'

interface Props {
  edaReport: EdaReport
}

export default function EdaChartsView({ edaReport }: Props) {
  const { numeric_distributions, categorical_breakdowns, correlation_matrix, time_trends } = edaReport

  const numCols = Object.keys(numeric_distributions || {})
  const catCols = Object.keys(categorical_breakdowns || {})
  const corrCols = Object.keys(correlation_matrix || {})

  return (
    <div className="space-y-8">
      {/* 1. Numerical Distributions */}
      {numCols.length > 0 && (
        <section className="space-y-4">
          <div className="border-b border-slate-800 pb-2">
            <h3 className="text-base font-semibold text-slate-100">Numerical Value Distributions</h3>
            <p className="text-xs text-slate-400">Histograms revealing distribution shapes, skewness, and spread.</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {numCols.map((col) => {
              const dist = numeric_distributions[col]
              return (
                <div key={col} className="glass rounded-2xl p-4 flex flex-col h-72">
                  <h4 className="text-xs font-medium text-slate-300 mb-2">{col} Distribution</h4>
                  <div className="flex-1 w-full min-h-0 overflow-hidden">
                    <Plot
                      data={[
                        {
                          type: 'bar',
                          x: dist.bins.slice(0, -1).map(String),
                          y: dist.counts,
                          marker: { color: '#22d3ee' },
                        },
                      ]}
                      layout={{
                        autosize: true,
                        margin: { l: 40, r: 15, t: 20, b: 35 },
                        paper_bgcolor: 'rgba(0,0,0,0)',
                        plot_bgcolor: 'rgba(0,0,0,0)',
                        font: { color: '#94a3b8', size: 10 },
                        xaxis: { title: { text: col }, showgrid: false },
                        yaxis: { title: { text: 'Frequency' }, gridcolor: '#1e293b' },
                      }}
                      style={{ width: '100%', height: '100%' }}
                      useResizeHandler={true}
                      config={{ displayModeBar: false, responsive: true }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* 2. Categorical Breakdowns */}
      {catCols.length > 0 && (
        <section className="space-y-4">
          <div className="border-b border-slate-800 pb-2">
            <h3 className="text-base font-semibold text-slate-100">Categorical Frequency Summaries</h3>
            <p className="text-xs text-slate-400">Distribution of top categories across discrete fields.</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {catCols.map((col) => {
              const items = categorical_breakdowns[col]
              return (
                <div key={col} className="glass rounded-2xl p-4 flex flex-col h-72">
                  <h4 className="text-xs font-medium text-slate-300 mb-2">{col} Frequencies</h4>
                  <div className="flex-1 w-full min-h-0 overflow-hidden">
                    <Plot
                      data={[
                        {
                          type: 'bar',
                          x: items.map((i) => i.category),
                          y: items.map((i) => i.count),
                          marker: { color: '#818cf8' },
                        },
                      ]}
                      layout={{
                        autosize: true,
                        margin: { l: 40, r: 15, t: 20, b: 45 },
                        paper_bgcolor: 'rgba(0,0,0,0)',
                        plot_bgcolor: 'rgba(0,0,0,0)',
                        font: { color: '#94a3b8', size: 10 },
                        xaxis: { tickangle: -25, showgrid: false },
                        yaxis: { title: { text: 'Count' }, gridcolor: '#1e293b' },
                      }}
                      style={{ width: '100%', height: '100%' }}
                      useResizeHandler={true}
                      config={{ displayModeBar: false, responsive: true }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* 3. Correlation Matrix */}
      {corrCols.length >= 2 && (
        <section className="space-y-4">
          <div className="border-b border-slate-800 pb-2">
            <h3 className="text-base font-semibold text-slate-100">Correlation Matrix (Pearson)</h3>
            <p className="text-xs text-slate-400">Pairwise linear associations. High positive or negative values indicate co-movement.</p>
          </div>
          <div className="glass rounded-2xl p-4 h-80">
            <div className="h-full w-full overflow-hidden">
              <Plot
                data={[
                  {
                    type: 'heatmap',
                    x: corrCols,
                    y: corrCols,
                    z: corrCols.map((r) => corrCols.map((c) => correlation_matrix[r]?.[c] ?? 0)),
                    colorscale: 'Blues',
                    zmin: -1,
                    zmax: 1,
                  },
                ]}
                layout={{
                  autosize: true,
                  margin: { l: 80, r: 30, t: 20, b: 60 },
                  paper_bgcolor: 'rgba(0,0,0,0)',
                  plot_bgcolor: 'rgba(0,0,0,0)',
                  font: { color: '#cbd5e1', size: 10 },
                  xaxis: { tickangle: -30 },
                }}
                style={{ width: '100%', height: '100%' }}
                useResizeHandler={true}
                config={{ displayModeBar: false, responsive: true }}
              />
            </div>
          </div>
        </section>
      )}

      {/* 4. Time Series Trend if available */}
      {time_trends && time_trends.dates && time_trends.dates.length > 2 && (
        <section className="space-y-4">
          <div className="border-b border-slate-800 pb-2">
            <h3 className="text-base font-semibold text-slate-100">
              Temporal Trend: {time_trends.target_column} over {time_trends.date_column}
            </h3>
            <p className="text-xs text-slate-400">Chronological aggregated trajectory.</p>
          </div>
          <div className="glass rounded-2xl p-4 h-72">
            <div className="h-full w-full overflow-hidden">
              <Plot
                data={[
                  {
                    type: 'scatter',
                    mode: 'lines+markers',
                    x: time_trends.dates,
                    y: time_trends.values,
                    line: { color: '#34d399', width: 2 },
                    marker: { color: '#10b981', size: 5 },
                  },
                ]}
                layout={{
                  autosize: true,
                  margin: { l: 50, r: 20, t: 20, b: 40 },
                  paper_bgcolor: 'rgba(0,0,0,0)',
                  plot_bgcolor: 'rgba(0,0,0,0)',
                  font: { color: '#94a3b8', size: 10 },
                  xaxis: { title: { text: time_trends.date_column || '' }, gridcolor: '#1e293b' },
                  yaxis: { title: { text: time_trends.target_column || '' }, gridcolor: '#1e293b' },
                }}
                style={{ width: '100%', height: '100%' }}
                useResizeHandler={true}
                config={{ displayModeBar: false, responsive: true }}
              />
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
