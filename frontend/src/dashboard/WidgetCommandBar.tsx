import { Command, Redo2, Undo2 } from 'lucide-react'
import { useState } from 'react'
import { llmService } from '../services/llmService'
import { applyCommand } from './CommandActionExecutor'
import type { Widget } from '../types/dashboard'

interface Props {
  dashboardId: number
  datasetId: number
  widgets: Widget[]
  onWidgetsChange: (widgets: Widget[]) => void
  onUndo: () => void
  onRedo: () => void
  canUndo: boolean
  canRedo: boolean
}

export default function WidgetCommandBar({
  dashboardId,
  datasetId,
  widgets,
  onWidgetsChange,
  onUndo,
  onRedo,
  canUndo,
  canRedo,
}: Props) {
  const [value, setValue] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)

  async function run() {
    const text = value.trim()
    if (!text) return
    setLoading(true)
    setStatus('')

    try {
      const parsed = await llmService.command(datasetId, text)
      const result = await applyCommand(dashboardId, datasetId, parsed, widgets)
      if (result.applied) {
        onWidgetsChange(result.widgets)
      }
      setStatus(result.message)
    } catch (err) {
      setStatus(err instanceof Error ? err.message : 'Command failed')
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
          placeholder='Try: "Add a donut chart of revenue by region"'
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') run()
          }}
          disabled={loading}
        />
        <button
          onClick={onUndo}
          disabled={!canUndo}
          className="rounded-lg border border-slate-700 p-1 text-slate-300 hover:border-cyan-400/50 disabled:opacity-40"
          title="Undo"
        >
          <Undo2 size={14} />
        </button>
        <button
          onClick={onRedo}
          disabled={!canRedo}
          className="rounded-lg border border-slate-700 p-1 text-slate-300 hover:border-cyan-400/50 disabled:opacity-40"
          title="Redo"
        >
          <Redo2 size={14} />
        </button>
        <button
          onClick={run}
          disabled={loading}
          className="rounded-lg bg-cyan-400 px-3 py-1 text-xs font-semibold text-slate-950 hover:bg-cyan-300 disabled:opacity-50"
        >
          {loading ? '...' : 'Run'}
        </button>
      </div>

      {status && <div className="rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2 text-xs text-slate-300">{status}</div>}
    </div>
  )
}
