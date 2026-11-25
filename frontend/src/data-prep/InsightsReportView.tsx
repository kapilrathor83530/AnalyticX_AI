import { AlertOctagon, BarChart, CheckCircle2, ChevronRight, Compass, Info, Lightbulb, TrendingUp } from 'lucide-react'
import type { EdaReport, InsightItem } from '../types'

interface Props {
  edaReport: EdaReport
}

export default function InsightsReportView({ edaReport }: Props) {
  const { insights_report, data_dictionary } = edaReport

  function renderSection(
    title: string,
    subtitle: string,
    icon: React.ReactNode,
    items?: InsightItem[]
  ) {
    if (!items || items.length === 0) return null

    return (
      <section className="glass rounded-3xl p-6 space-y-4">
        <div className="flex items-center gap-3 border-b border-slate-800 pb-3">
          <div className="rounded-xl bg-slate-800/80 p-2 text-cyan-300">{icon}</div>
          <div>
            <h3 className="text-base font-semibold text-slate-100">{title}</h3>
            <p className="text-xs text-slate-400">{subtitle}</p>
          </div>
        </div>

        <ul className="space-y-3.5">
          {items.map((item) => (
            <li key={item.id} className="rounded-2xl border border-slate-800/60 bg-slate-900/30 p-4 space-y-2">
              <div className="flex items-start gap-2.5">
                <span className="mt-1 flex h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-400" />
                <p className="text-sm font-medium leading-relaxed text-slate-200">{item.statement}</p>
              </div>
              <div className="flex items-center gap-2 pl-4 text-xs text-slate-400">
                <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[10px] text-cyan-200">Verified Evidence</span>
                <span>{item.evidence}</span>
              </div>
            </li>
          ))}
        </ul>
      </section>
    )
  }

  return (
    <div className="space-y-6">
      {/* 1. Dataset Summary */}
      {renderSection(
        '1. Dataset Summary & Scope',
        'Structural overview, record dimensions, and completeness baseline.',
        <Info size={18} />,
        insights_report.dataset_summary
      )}

      {/* 2. Column-Level Findings */}
      {renderSection(
        '2. Column-Level Statistical Findings',
        'Observed numerical distributions, spreads, and dominant categorical frequencies.',
        <BarChart size={18} />,
        insights_report.column_findings
      )}

      {/* 3. Relationships & Correlations */}
      <section className="glass rounded-3xl p-6 space-y-4">
        <div className="flex items-center gap-3 border-b border-slate-800 pb-3">
          <div className="rounded-xl bg-slate-800/80 p-2 text-cyan-300">
            <TrendingUp size={18} />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-100">3. Relationships & Correlations</h3>
            <p className="text-xs text-slate-400">Pairwise interactions observed among quantitative metrics.</p>
          </div>
        </div>

        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-3.5 py-2 text-xs text-amber-300 flex items-center gap-2">
          <Info size={14} className="shrink-0" />
          <span>Important statistical safeguard: High correlation measures linear co-occurrence and does not establish causality.</span>
        </div>

        <ul className="space-y-3.5">
          {insights_report.relationships.map((item) => (
            <li key={item.id} className="rounded-2xl border border-slate-800/60 bg-slate-900/30 p-4 space-y-2">
              <div className="flex items-start gap-2.5">
                <span className="mt-1 flex h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-400" />
                <p className="text-sm font-medium leading-relaxed text-slate-200">{item.statement}</p>
              </div>
              <div className="flex items-center gap-2 pl-4 text-xs text-slate-400">
                <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[10px] text-cyan-200">Verified Evidence</span>
                <span>{item.evidence}</span>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {/* 4. Anomalies & Outliers */}
      {renderSection(
        '4. Anomalies & Extreme Observations',
        'Notable tail deviations, potential business surges, or data anomalies.',
        <AlertOctagon size={18} />,
        insights_report.anomalies
      )}

      {/* 5. Business Insights */}
      {renderSection(
        '5. Core Business & Segment Insights',
        'Strategic insights derived from revenue, volume, customer, and regional parameters.',
        <Lightbulb size={18} />,
        insights_report.business_insights
      )}

      {/* 6. Recommended Next Steps */}
      {renderSection(
        '6. Recommended Next Steps & Explorations',
        'Actionable follow-up investigations, visual deep-dives, and simulation targets.',
        <Compass size={18} />,
        insights_report.recommended_next_steps
      )}

      {/* 7. Data Dictionary Table */}
      {data_dictionary && data_dictionary.length > 0 && (
        <section className="glass rounded-3xl p-6 space-y-4">
          <div className="border-b border-slate-800 pb-3">
            <h3 className="text-base font-semibold text-slate-100">7. Data Dictionary & Field Catalog</h3>
            <p className="text-xs text-slate-400">Catalog of profiled attributes, inferred analytical roles, and completeness ratios.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-2.5 pr-4">Field Name</th>
                  <th className="py-2.5 pr-4">Data Type</th>
                  <th className="py-2.5 pr-4">Analytical Role</th>
                  <th className="py-2.5 pr-4">Distinct Count</th>
                  <th className="py-2.5 pr-4">Missing %</th>
                  <th className="py-2.5">Sample Values</th>
                </tr>
              </thead>
              <tbody>
                {data_dictionary.map((field) => (
                  <tr key={field.name} className="border-b border-slate-800/40 hover:bg-slate-800/20">
                    <td className="py-2.5 pr-4 font-mono font-medium text-slate-200">{field.name}</td>
                    <td className="py-2.5 pr-4 text-slate-400">{field.dtype}</td>
                    <td className="py-2.5 pr-4 text-cyan-300 font-medium">{field.role_hint}</td>
                    <td className="py-2.5 pr-4 text-slate-300">{field.unique_count.toLocaleString()}</td>
                    <td className="py-2.5 pr-4">
                      <span className={field.missing_count > 0 ? 'text-amber-300' : 'text-slate-400'}>
                        {field.missing_percent}%
                      </span>
                    </td>
                    <td className="py-2.5 text-slate-400 font-mono text-[11px]">
                      {field.sample_values?.slice(0, 3).map(String).join(', ') || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}
