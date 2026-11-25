import {
  ChevronDown,
  Download,
  ExternalLink,
  FileSpreadsheet,
  FileText,
  Layers,
  RefreshCw,
  Search,
  Trash2,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getErrorMessage } from '../api/client'
import { dashboardService } from '../services/dashboardService'
import { reportService } from '../services/reportService'
import type { Dashboard } from '../types/dashboard'

export default function SavedDashboardsPage() {
  const [items, setItems] = useState<Dashboard[]>([])
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')
  const [activeDownloadId, setActiveDownloadId] = useState<number | null>(null)
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null)

  async function load(query = search) {
    try {
      setItems(await dashboardService.list(undefined, query))
      setError('')
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  useEffect(() => {
    load('')
  }, [])

  async function duplicate(item: Dashboard) {
    const copy = await dashboardService.duplicate(item.id)
    setItems((list) => [copy, ...list])
  }

  async function remove(item: Dashboard) {
    if (!window.confirm(`Delete “${item.name}”? This cannot be undone.`)) return
    await dashboardService.remove(item.id)
    setItems((list) => list.filter((row) => row.id !== item.id))
  }

  async function downloadConfig(item: Dashboard) {
    const content = await dashboardService.exportConfig(item.id)
    const blob = new Blob([JSON.stringify(content, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${item.name.replace(/[^a-z0-9]+/gi, '-') || 'dashboard'}.json`
    anchor.click()
    URL.revokeObjectURL(url)
    setActiveDownloadId(null)
  }

  async function downloadReport(item: Dashboard, format: 'xlsx' | 'pdf') {
    try {
      setDownloadingFormat(format)
      const cleanName = item.name.replace(/[^a-zA-Z0-9_-]/g, '_')
      await reportService.downloadDirect(
        `/reports/dashboard/${item.dataset_id}/download?format=${format}`,
        `Analyticx_Dashboard_${cleanName}.${format}`
      )
      setActiveDownloadId(null)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setDownloadingFormat(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold flex items-center gap-2">
            <Layers className="text-cyan-400" size={24} />
            Saved Dashboards
          </h1>
          <p className="text-sm text-slate-400">
            Interactive dashboard projects, multi-widget grids, and executive visual exports.
          </p>
        </div>

        <form
          onSubmit={(event) => {
            event.preventDefault()
            load()
          }}
          className="flex gap-2"
        >
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search dashboards..."
            className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-cyan-400 focus:outline-none"
          />
          <button className="rounded-xl bg-cyan-400 px-3 py-2 text-slate-950 font-bold hover:bg-cyan-300 transition">
            <Search size={16} />
          </button>
        </form>
      </div>

      {error && <p className="rounded-xl bg-red-500/10 border border-red-500/30 p-3 text-sm text-red-200">{error}</p>}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => (
          <article
            key={item.id}
            className="glass rounded-2xl p-5 border border-slate-800 flex flex-col justify-between space-y-4"
          >
            <div>
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-slate-100">{item.name}</h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                  Dataset #{item.dataset_id}
                </span>
              </div>
              <p className="mt-2 text-xs text-slate-400 line-clamp-2">
                {item.description || 'No description provided.'}
              </p>
              <p className="mt-3 text-[11px] text-slate-500 font-mono">
                Modified {new Date(item.updated_at || item.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800/80">
              <Link
                to={`/dashboard/${item.id}/edit`}
                className="inline-flex items-center gap-1 rounded-xl bg-cyan-400 px-3 py-1.5 text-xs font-bold text-slate-950 hover:bg-cyan-300 transition"
              >
                <ExternalLink size={13} /> Open
              </Link>

              <button
                onClick={() => duplicate(item)}
                className="rounded-xl border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-800 transition"
              >
                Duplicate
              </button>

              {/* Download Dropdown */}
              <div className="relative">
                <button
                  onClick={() => setActiveDownloadId(activeDownloadId === item.id ? null : item.id)}
                  title="Download Dashboard"
                  className="rounded-xl border border-slate-700 p-1.5 text-slate-300 hover:bg-slate-800 hover:text-cyan-300 transition flex items-center gap-0.5"
                >
                  <Download size={14} />
                  <ChevronDown size={10} className="text-slate-500" />
                </button>

                {activeDownloadId === item.id && (
                  <div className="absolute right-0 bottom-full mb-2 z-50 w-52 rounded-2xl border border-slate-700 bg-slate-950 p-2 shadow-2xl backdrop-blur-xl animate-in fade-in zoom-in-95 duration-100">
                    <div className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-800 mb-1">
                      Download Options
                    </div>
                    <button
                      onClick={() => downloadReport(item, 'xlsx')}
                      disabled={downloadingFormat !== null}
                      className="w-full flex items-center gap-2 px-2.5 py-1.5 text-xs text-left text-slate-200 hover:bg-slate-800 rounded-xl transition"
                    >
                      <FileSpreadsheet size={14} className="text-emerald-400" />
                      <span>{downloadingFormat === 'xlsx' ? 'Generating...' : 'Excel Workbook (.xlsx)'}</span>
                    </button>
                    <button
                      onClick={() => downloadReport(item, 'pdf')}
                      disabled={downloadingFormat !== null}
                      className="w-full flex items-center gap-2 px-2.5 py-1.5 text-xs text-left text-slate-200 hover:bg-slate-800 rounded-xl transition"
                    >
                      <FileText size={14} className="text-red-400" />
                      <span>{downloadingFormat === 'pdf' ? 'Generating...' : 'Dashboard PDF (.pdf)'}</span>
                    </button>
                    <button
                      onClick={() => downloadConfig(item)}
                      className="w-full flex items-center gap-2 px-2.5 py-1.5 text-xs text-left text-slate-200 hover:bg-slate-800 rounded-xl transition"
                    >
                      <FileText size={14} className="text-purple-400" />
                      <span>Config JSON (.json)</span>
                    </button>
                  </div>
                )}
              </div>

              <button
                onClick={() => remove(item)}
                title="Delete dashboard"
                className="rounded-xl border border-red-700/50 p-1.5 text-red-300 hover:bg-red-500/10 transition ml-auto"
              >
                <Trash2 size={14} />
              </button>
            </div>
          </article>
        ))}
      </div>

      {!items.length && (
        <div className="glass rounded-2xl p-10 text-center text-sm text-slate-400">
          No saved dashboards match this search.
        </div>
      )}
    </div>
  )
}
