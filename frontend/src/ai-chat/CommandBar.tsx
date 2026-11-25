import { Command } from 'lucide-react'
import { useState } from 'react'
import { llmService } from '../services/llmService'
import type { CommandResponse } from '../types/llm'

interface Props {
  datasetId: number
  onAction?: (response: CommandResponse) => void
}

export default function CommandBar({ datasetId, onAction }: Props) {
  const [value, setValue] = useState('')
  const [result, setResult] = useState<CommandResponse | null>(null)
  const [loading, setLoading] = useState(false)

  async function submit() {
    const text = value.trim()
    if (!text) return

    setLoading(true)
    setResult(null)

    try {
      const response = await llmService.command(datasetId, text)
      setResult(response)
      onAction?.(response)
    } finally {
      setLoading(false)
      setValue('')
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2">
        <Command size={16} className="text-cyan-300" />
        <input
          className="flex-1 bg-transparent text-sm outline-none"
          placeholder='Try: "Show revenue by region as a bar chart"'
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') submit()
          }}
          disabled={loading}
        />
        <button
          onClick={submit}
          disabled={loading}
          className="rounded-lg bg-cyan-400 px-3 py-1 text-xs font-semibold text-slate-950 hover:bg-cyan-300 disabled:opacity-50"
        >
          {loading ? '...' : 'Run'}
        </button>
      </div>

      {result && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-xs text-slate-300">
          <div>
            <span className="text-slate-400">Action:</span> {result.action}
          </div>
          {result.chart_type && (
            <div>
              <span className="text-slate-400">Chart:</span> {result.chart_type}
            </div>
          )}
          {Object.keys(result.data_mapping).length > 0 && (
            <div>
              <span className="text-slate-400">Mapping:</span>{' '}
              {JSON.stringify(result.data_mapping)}
            </div>
          )}
          {result.clarification_needed && (
            <div className="mt-1 text-amber-300">{result.clarification_question}</div>
          )}
          {!result.available && <div className="mt-1 text-red-300">Local LLM is not available.</div>}
        </div>
      )}
    </div>
  )
}
