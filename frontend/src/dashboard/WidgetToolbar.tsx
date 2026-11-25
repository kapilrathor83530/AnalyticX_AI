import {
  ChevronDown,
  Copy,
  Download,
  FileSpreadsheet,
  FileText,
  Filter,
  Image as ImageIcon,
  RefreshCw,
  RotateCcw,
  Settings,
  Trash2,
} from 'lucide-react'
import { useState } from 'react'
import type { Widget } from '../types/dashboard'
import { dashboardService } from '../services/dashboardService'
import { reportService, triggerBrowserDownload } from '../services/reportService'

interface Props {
  widget: Widget
  datasetId?: number
  onFilter: () => void
  onEdit: () => void
  onDuplicate: () => void
  onReset: () => void
  onRemove: () => void
}

export default function WidgetToolbar({
  widget,
  datasetId,
  onFilter,
  onEdit,
  onDuplicate,
  onReset,
  onRemove,
}: Props) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [downloading, setDownloading] = useState<string | null>(null)

  const button = 'rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-cyan-300 transition'
  const stop = (event: React.PointerEvent | React.MouseEvent) => event.stopPropagation()

  // 1. Export Plotted Data (CSV / XLSX)
  const handleExportData = async (format: 'csv' | 'xlsx') => {
    try {
      setDownloading(format)
      setMenuOpen(false)

      let rows: Record<string, unknown>[] = []
      let columns: string[] = []

      if (datasetId) {
        try {
          const res = await dashboardService.renderChart(datasetId, {
            chart_type: widget.chart_type,
            data_mapping: widget.data_mapping || {},
            aggregation: (widget.config?.aggregation as string) || 'sum',
            filters: (widget.config?.visual_filters as any) || [],
            appearance: (widget.config?.appearance as any) || {},
            title: widget.title,
          })
          rows = res.data || []
        } catch {
          // fallback if render request fails
        }
      }

      if (rows.length > 0) {
        columns = Object.keys(rows[0])
      } else {
        const x = String(widget.data_mapping?.x || 'dimension')
        const y = String(widget.data_mapping?.y || 'metric')
        columns = [x, y]
        rows = [{ [x]: 'No plotted data points', [y]: 0 }]
      }

      await reportService.exportChartData({
        title: widget.title || 'Chart_Data',
        columns,
        rows,
        format,
      })
    } catch (err) {
      console.error('Failed to export chart data', err)
    } finally {
      setDownloading(null)
    }
  }

  // 2. Export Chart Image (PNG / SVG)
  const handleExportImage = async (format: 'png' | 'svg') => {
    try {
      setDownloading(format)
      setMenuOpen(false)

      const cleanTitle = (widget.title || 'Chart').replace(/[^a-zA-Z0-9_-]/g, '_')
      const container = document.getElementById(`widget-container-${widget.id}`)
      const plotEl = container?.querySelector('.js-plotly-plot') as any

      if (plotEl && (window as any).Plotly) {
        try {
          const url = await (window as any).Plotly.toImage(plotEl, {
            format,
            width: 1200,
            height: 800,
          })
          const a = document.createElement('a')
          a.href = url
          a.download = `${cleanTitle}.${format}`
          document.body.appendChild(a)
          a.click()
          document.body.removeChild(a)
          return
        } catch (e) {
          console.warn('Plotly.toImage fallback to DOM SVG serializer', e)
        }
      }

      // DOM SVG Fallback
      const svgEl = container?.querySelector('svg.main-svg') || container?.querySelector('svg')
      if (svgEl) {
        const svgData = new XMLSerializer().serializeToString(svgEl)
        if (format === 'svg') {
          const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
          triggerBrowserDownload(blob, `${cleanTitle}.svg`)
        } else {
          const canvas = document.createElement('canvas')
          const bbox = svgEl.getBoundingClientRect()
          canvas.width = (bbox.width || 800) * 2
          canvas.height = (bbox.height || 500) * 2
          const ctx = canvas.getContext('2d')
          const img = new Image()
          img.onload = () => {
            if (ctx) {
              ctx.fillStyle = '#090d16'
              ctx.fillRect(0, 0, canvas.width, canvas.height)
              ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
              canvas.toBlob((blob) => {
                if (blob) triggerBrowserDownload(blob, `${cleanTitle}.png`)
              }, 'image/png')
            }
          }
          img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)))
        }
      }
    } catch (err) {
      console.error('Failed to export chart image', err)
    } finally {
      setDownloading(null)
    }
  }

  return (
    <div
      className="widget-controls relative flex cursor-default items-center gap-1"
      onPointerDown={stop}
      onMouseDown={stop}
    >
      {/* Download Dropdown */}
      <div className="relative">
        <button
          title={`Download chart or data for ${widget.title}`}
          onClick={() => setMenuOpen(!menuOpen)}
          className={`flex items-center gap-0.5 ${button} ${menuOpen ? 'bg-slate-800 text-cyan-300' : ''}`}
        >
          {downloading ? <RefreshCw size={14} className="animate-spin text-cyan-400" /> : <Download size={14} />}
          <ChevronDown size={10} className="text-slate-500" />
        </button>

        {menuOpen && (
          <div className="absolute right-0 top-full mt-1.5 z-50 w-52 rounded-xl border border-slate-700 bg-slate-950 p-1.5 shadow-2xl backdrop-blur-xl animate-in fade-in zoom-in-95 duration-100">
            <div className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-800/80 mb-1">
              Export Graphic
            </div>
            <button
              onClick={() => handleExportImage('png')}
              className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-left text-xs text-slate-300 hover:bg-slate-800 hover:text-cyan-300 transition"
            >
              <ImageIcon size={13} className="text-cyan-400" />
              <span>Download PNG Image</span>
            </button>
            <button
              onClick={() => handleExportImage('svg')}
              className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-left text-xs text-slate-300 hover:bg-slate-800 hover:text-cyan-300 transition"
            >
              <ImageIcon size={13} className="text-purple-400" />
              <span>Download SVG Vector</span>
            </button>

            <div className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-800/80 my-1">
              Export Plotted Data
            </div>
            <button
              onClick={() => handleExportData('csv')}
              className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-left text-xs text-slate-300 hover:bg-slate-800 hover:text-cyan-300 transition"
            >
              <FileText size={13} className="text-blue-400" />
              <span>Export Data (CSV)</span>
            </button>
            <button
              onClick={() => handleExportData('xlsx')}
              className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-left text-xs text-slate-300 hover:bg-slate-800 hover:text-cyan-300 transition"
            >
              <FileSpreadsheet size={13} className="text-emerald-400" />
              <span>Export Data (Excel XLSX)</span>
            </button>
          </div>
        )}
      </div>

      <button title="Open visual filters" onClick={onFilter} className={button}>
        <Filter size={14} />
      </button>
      <button title="Edit chart" onClick={onEdit} className={button}>
        <Settings size={14} />
      </button>
      <button title="Duplicate visual" onClick={onDuplicate} className={button}>
        <Copy size={14} />
      </button>
      <button title="Reset visual filters" onClick={onReset} className={button}>
        <RotateCcw size={14} />
      </button>
      <button
        title={`Remove ${widget.title}`}
        onClick={onRemove}
        className="rounded-lg p-1.5 text-slate-400 hover:bg-red-500/10 hover:text-red-300 transition"
      >
        <Trash2 size={14} />
      </button>
    </div>
  )
}
