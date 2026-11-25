import {
  Check,
  Clock,
  Copy,
  Edit2,
  ExternalLink,
  History,
  Play,
  Star,
  Trash2,
} from 'lucide-react'
import { useState } from 'react'
import type { QueryHistoryRecord } from '../../services/sqlStudioService'

interface Props {
  history: QueryHistoryRecord[]
  onSelectQuery: (sql: string) => void
  onToggleFavorite: (id: string) => void
  onRenameQuery: (id: string, name: string) => void
  onDeleteQuery: (id: string) => void
  onClearHistory: () => void
}

export default function QueryHistoryPanel({
  history,
  onSelectQuery,
  onToggleFavorite,
  onRenameQuery,
  onDeleteQuery,
  onClearHistory,
}: Props) {
  const [activeTab, setActiveTab] = useState<'recent' | 'saved'>('recent')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const items = activeTab === 'saved' ? history.filter((h) => h.is_favorite) : history

  const handleCopy = (id: string, query: string, e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(query)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 1800)
  }

  const handleStartRename = (id: string, currentName: string = '', e: React.MouseEvent) => {
    e.stopPropagation()
    setEditingId(id)
    setEditName(currentName)
  }

  const handleSaveRename = (id: string) => {
    onRenameQuery(id, editName.trim())
    setEditingId(null)
  }

  return (
    <div className="space-y-3">
      {/* Drawer Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center rounded-xl border border-slate-800 bg-slate-900/80 p-0.5 text-xs">
          <button
            onClick={() => setActiveTab('recent')}
            className={`rounded-lg px-2.5 py-1 text-[11px] font-semibold transition ${
              activeTab === 'recent'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Recent ({history.length})
          </button>
          <button
            onClick={() => setActiveTab('saved')}
            className={`rounded-lg px-2.5 py-1 text-[11px] font-semibold transition ${
              activeTab === 'saved'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Saved ({history.filter((h) => h.is_favorite).length})
          </button>
        </div>

        {history.length > 0 && activeTab === 'recent' && (
          <button
            onClick={onClearHistory}
            className="text-[10px] text-slate-500 hover:text-red-300 transition"
          >
            Clear Log
          </button>
        )}
      </div>

      {/* History Items List */}
      <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
        {items.length === 0 ? (
          <div className="text-center py-8 text-[11px] text-slate-500">
            {activeTab === 'saved'
              ? 'No starred or saved queries yet. Star any query to save it.'
              : 'No queries executed yet.'}
          </div>
        ) : (
          items.map((item) => (
            <div
              key={item.id}
              onClick={() => onSelectQuery(item.query)}
              className="group rounded-xl border border-slate-800/80 bg-slate-900/40 hover:border-cyan-500/40 hover:bg-slate-900/80 p-2.5 text-xs transition cursor-pointer space-y-1.5"
            >
              <div className="flex items-center justify-between">
                {editingId === item.id ? (
                  <div
                    className="flex items-center gap-1 w-full"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      type="text"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSaveRename(item.id)}
                      placeholder="Name query..."
                      className="flex-1 rounded border border-slate-700 bg-slate-950 px-1.5 py-0.5 text-[11px] text-slate-200"
                    />
                    <button
                      onClick={() => handleSaveRename(item.id)}
                      className="text-[10px] bg-cyan-500 text-slate-950 font-bold px-1.5 py-0.5 rounded"
                    >
                      Save
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5 min-w-0 flex-1">
                    <span
                      className={`h-1.5 w-1.5 rounded-full shrink-0 ${
                        item.status === 'success' ? 'bg-emerald-400' : 'bg-red-400'
                      }`}
                    />
                    <span className="font-semibold text-slate-200 text-[11px] truncate">
                      {item.name || item.query.slice(0, 32)}
                    </span>
                  </div>
                )}

                <div className="flex items-center gap-1 shrink-0 ml-1">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onToggleFavorite(item.id)
                    }}
                    title={item.is_favorite ? 'Unstar' : 'Star query'}
                    className="text-slate-500 hover:text-amber-400 transition p-0.5"
                  >
                    <Star
                      size={12}
                      className={item.is_favorite ? 'fill-amber-400 text-amber-400' : ''}
                    />
                  </button>

                  <button
                    onClick={(e) => handleCopy(item.id, item.query, e)}
                    title="Copy query"
                    className="text-slate-500 hover:text-slate-300 transition p-0.5"
                  >
                    {copiedId === item.id ? (
                      <Check size={12} className="text-emerald-400" />
                    ) : (
                      <Copy size={12} />
                    )}
                  </button>

                  <button
                    onClick={(e) => handleStartRename(item.id, item.name, e)}
                    title="Rename"
                    className="text-slate-500 hover:text-slate-300 transition p-0.5"
                  >
                    <Edit2 size={11} />
                  </button>

                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onDeleteQuery(item.id)
                    }}
                    title="Delete"
                    className="text-slate-500 hover:text-red-400 transition p-0.5"
                  >
                    <Trash2 size={11} />
                  </button>
                </div>
              </div>

              {/* Code preview snippet */}
              <p className="text-[10px] font-mono text-cyan-300/80 truncate">
                {item.query.replace(/\s+/g, ' ')}
              </p>

              {/* Metric stats */}
              <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono pt-1 border-t border-slate-800/40">
                <span>
                  {item.row_count !== undefined ? `${item.row_count} rows` : ''}
                  {item.execution_time_ms ? ` · ${item.execution_time_ms}ms` : ''}
                </span>
                <span>{item.timestamp}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
