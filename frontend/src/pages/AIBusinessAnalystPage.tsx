import { ArrowLeft, BrainCircuit, Check, Copy, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import AIChatPanel from '../ai-chat/AIChatPanel'
import ChartRenderer from '../visualization-studio/ChartRenderer'
import { agentService } from '../services/agentService'
import type { AgentQueryResponse } from '../types/agent'

const PRESET_QUERIES = [
  'Identify top revenue drivers & key performance indicators',
  'Detect outliers, anomalies, and data quality issues',
  'Analyze distribution patterns and column correlations',
  'Summarize strategic business risks and optimization opportunities',
]

export default function AIBusinessAnalystPage() {
  const { id } = useParams()
  const datasetId = Number(id)

  const [question, setQuestion] = useState('')
  const [response, setResponse] = useState<AgentQueryResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [useLlm, setUseLlm] = useState(true)
  const [copied, setCopied] = useState(false)

  async function runQuery(customText?: string) {
    const text = (customText ?? question).trim()
    if (!text) return
    setLoading(true)
    setResponse(null)
    try {
      const result = await agentService.query(datasetId, text, useLlm)
      setResponse(result)
    } finally {
      setLoading(false)
    }
  }

  function handlePresetClick(preset: string) {
    setQuestion(preset)
    runQuery(preset)
  }

  function handleCopyAnswer() {
    if (!response?.answer) return
    navigator.clipboard.writeText(response.answer)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const backUrl = datasetId ? `/datasets/${datasetId}` : '/workspace'

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Link
          to={backUrl}
          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-xs text-cyan-300 transition hover:border-cyan-500/50 hover:bg-slate-800"
        >
          <ArrowLeft size={14} />
          Back to Dataset Studio
        </Link>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-300">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Deterministic Python Engine Active
          </span>
        </div>
      </div>

      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
          <BrainCircuit className="text-cyan-400" size={26} />
          AI Business Analyst
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Formulate executive business questions. The agentic system combines verified Python statistics with local LLM reasoning.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="glass space-y-4 rounded-3xl p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
              <Sparkles size={16} className="text-cyan-400" />
              Agent Workflow & Queries
            </h2>
            <span className="text-xs text-slate-400">Dataset #{datasetId}</span>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-400">Executive Preset Prompts</label>
            <div className="flex flex-wrap gap-2">
              {PRESET_QUERIES.map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => handlePresetClick(preset)}
                  className="rounded-lg border border-slate-800 bg-slate-900/70 px-2.5 py-1 text-xs text-slate-300 transition hover:border-cyan-500/50 hover:bg-cyan-500/10 hover:text-cyan-200"
                >
                  {preset}
                </button>
              ))}
            </div>
          </div>

          <textarea
            className="h-28 w-full rounded-2xl border border-slate-800 bg-slate-900/90 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:border-cyan-500/60 focus:outline-none focus:ring-1 focus:ring-cyan-500/60"
            placeholder="e.g. Which region generates the highest revenue with lowest return rates?"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
          />

          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={useLlm}
                onChange={(event) => setUseLlm(event.target.checked)}
                className="rounded border-slate-700 bg-slate-900 text-cyan-400 focus:ring-cyan-400/20"
              />
              Use local LLM for reasoning (Ollama / Qwen)
            </label>

            <button
              onClick={() => runQuery()}
              disabled={loading || !question.trim()}
              className="rounded-xl bg-cyan-400 px-4 py-2 text-xs font-semibold text-slate-950 hover:bg-cyan-300 disabled:opacity-50 transition shadow-sm shadow-cyan-950"
            >
              {loading ? 'Analyzing Data...' : 'Run Workflow'}
            </button>
          </div>

          {response?.chart_config && datasetId ? (
            <div className="h-[340px] rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
              <ChartRenderer
                datasetId={Number(datasetId)}
                chartType={String(response.chart_config.chart_type || 'bar')}
                dataMapping={(response.chart_config.data_mapping || {}) as Record<string, string | string[]>}
                appearance={(response.chart_config.appearance || {}) as Record<string, unknown>}
                title={response.chart_config.title}
                aggregation={response.chart_config.aggregation}
              />
            </div>
          ) : null}
          {response && (
            <div className="space-y-3 pt-2">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-cyan-400">Executive Answer</span>
                  <button
                    onClick={handleCopyAnswer}
                    className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 transition"
                  >
                    {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                    {copied ? 'Copied' : 'Copy'}
                  </button>
                </div>
                <div className="text-sm leading-relaxed text-slate-200 whitespace-pre-wrap">{response.answer}</div>
              </div>

              {response.verified_facts && response.verified_facts.length > 0 && (
                <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3 text-xs text-emerald-100">
                  <span className="font-semibold">Verified facts:</span>
                  <ul className="mt-1 list-disc pl-4 space-y-0.5">{response.verified_facts.map((f, i) => <li key={i}>{f}</li>)}</ul>
                </div>
              )}

              {response.limitations && response.limitations.length > 0 && (
                <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 text-xs text-amber-100">
                  <span className="font-semibold">Limitations:</span>
                  <ul className="mt-1 list-disc pl-4 space-y-0.5">{response.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul>
                </div>
              )}

              {response.missing_info.length > 0 && (
                <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
                  <span className="font-semibold">Missing information identified:</span> {response.missing_info.join(', ')}
                </div>
              )}

              <div>
                <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Agent Verification Steps</div>
                <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                  {response.steps.map((step, index) => (
                    <div
                      key={index}
                      className={`rounded-xl border p-2.5 text-xs ${
                        step.status === 'ok'
                          ? 'border-slate-800 bg-slate-900/50 text-slate-300'
                          : step.status === 'skipped'
                          ? 'border-amber-500/30 bg-amber-500/5 text-amber-200'
                          : 'border-red-500/30 bg-red-500/5 text-red-200'
                      }`}
                    >
                      <div className="font-semibold text-slate-200">
                        {step.agent} · <span className="text-cyan-400">{step.tool}</span>
                      </div>
                      <div className="text-slate-400 mt-0.5">{step.message}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </section>

        <section className="glass h-[620px] overflow-hidden rounded-3xl flex flex-col">
          <div className="border-b border-slate-800 p-4 bg-slate-900/40">
            <div className="text-sm font-semibold text-slate-200">Business Decision Chat</div>
            <p className="mt-0.5 text-xs text-slate-400">Grounded analytics reasoning with strict truth verification.</p>
          </div>
          <div className="flex-1 overflow-hidden">
            <AIChatPanel datasetId={datasetId} placeholder="Ask about revenue, cost, profit, customer churn, trends, or risks..." />
          </div>
        </section>
      </div>
    </div>
  )
}
