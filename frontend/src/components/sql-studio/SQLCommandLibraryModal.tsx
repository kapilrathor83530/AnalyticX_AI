import {
  BookOpen,
  Check,
  ChevronRight,
  Filter,
  Plus,
  Search,
  Sliders,
  Star,
  X,
  Zap,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import type { SchemaColumn } from '../../services/sqlStudioService'
import {
  SQL_COMMAND_TEMPLATES,
  type SQLTemplateItem,
} from './sqlTemplates'

interface Props {
  isOpen: boolean
  onClose: () => void
  onInsert: (sql: string) => void
  schemaColumns: SchemaColumn[]
}

export default function SQLCommandLibraryModal({
  isOpen,
  onClose,
  onInsert,
  schemaColumns,
}: Props) {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('All')
  const [favorites, setFavorites] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem('analyticx_sql_template_favorites')
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })

  // Template configuration modal state
  const [configuringTemplate, setConfiguringTemplate] = useState<SQLTemplateItem | null>(null)
  const [configParams, setConfigParams] = useState<Record<string, any>>({})

  const categories = [
    'All',
    'Favorites',
    'Basic',
    'Filtering',
    'Sorting & Limiting',
    'Aggregations',
    'Data Quality',
    'String Operations',
    'Date & Time',
    'Joins & CTEs',
    'Advanced Analytics',
  ]

  const numericCols = useMemo(() => schemaColumns.filter((c) => c.is_numeric), [schemaColumns])
  const categoricalCols = useMemo(() => schemaColumns.filter((c) => !c.is_numeric && !c.is_datetime), [schemaColumns])
  const dateCols = useMemo(() => schemaColumns.filter((c) => c.is_datetime || c.name.toLowerCase().includes('date') || c.name.toLowerCase().includes('year')), [schemaColumns])

  const toggleFavorite = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setFavorites((prev) => {
      const next = prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
      try {
        localStorage.setItem('analyticx_sql_template_favorites', JSON.stringify(next))
      } catch {
        // ignore
      }
      return next
    })
  }

  const filteredTemplates = useMemo(() => {
    return SQL_COMMAND_TEMPLATES.filter((t) => {
      if (selectedCategory === 'Favorites') {
        if (!favorites.includes(t.id)) return false
      } else if (selectedCategory !== 'All' && t.category !== selectedCategory) {
        return false
      }

      if (searchTerm.trim()) {
        const q = searchTerm.toLowerCase()
        const matchTitle = t.title.toLowerCase().includes(q)
        const matchDesc = t.description.toLowerCase().includes(q)
        const matchCat = t.category.toLowerCase().includes(q)
        if (!matchTitle && !matchDesc && !matchCat) return false
      }
      return true
    })
  }, [selectedCategory, searchTerm, favorites])

  const handleSelectTemplate = (template: SQLTemplateItem) => {
    if (template.requiresConfig && template.configFields) {
      // Initialize default parameters using real columns
      const initParams: Record<string, any> = {}
      template.configFields.forEach((f) => {
        if (f.type === 'numeric_column') {
          initParams[f.key] = numericCols.length > 0 ? numericCols[0].name : schemaColumns[0]?.name || ''
        } else if (f.type === 'categorical_column') {
          initParams[f.key] = categoricalCols.length > 0 ? categoricalCols[0].name : schemaColumns[0]?.name || ''
        } else if (f.type === 'date_column') {
          initParams[f.key] = dateCols.length > 0 ? dateCols[0].name : schemaColumns[0]?.name || ''
        } else if (f.type === 'any_column') {
          initParams[f.key] = schemaColumns[0]?.name || ''
        } else {
          initParams[f.key] = f.defaultValue !== undefined ? f.defaultValue : ''
        }
      })
      setConfigParams(initParams)
      setConfiguringTemplate(template)
    } else {
      const generated = template.generateQuery({})
      onInsert(generated)
      onClose()
    }
  }

  const handleApplyConfig = () => {
    if (!configuringTemplate) return
    const sql = configuringTemplate.generateQuery(configParams)
    onInsert(sql)
    setConfiguringTemplate(null)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="glass rounded-3xl border border-slate-700 bg-slate-950 p-6 max-w-4xl w-full max-h-[85vh] flex flex-col space-y-4 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="rounded-xl bg-purple-500/10 p-2 text-purple-400 border border-purple-500/20">
              <BookOpen size={18} />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-100">SQL Command & Template Library</h3>
              <p className="text-xs text-slate-400">
                Browse, search, parameterize, and insert verified SQLite queries grounded in your active schema.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-xl p-1.5 text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Search & Category Pills */}
        <div className="space-y-2.5">
          <div className="relative">
            <Search size={14} className="absolute left-3.5 top-3 text-slate-500" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by keyword, operation, or phrase (e.g. 'missing values', 'top products', 'month')..."
              className="w-full rounded-xl border border-slate-800 bg-slate-900/90 pl-9 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:border-cyan-400 focus:outline-none"
            />
          </div>

          <div className="flex flex-wrap items-center gap-1.5 overflow-x-auto pb-1 text-xs">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`rounded-xl px-3 py-1 text-xs font-medium transition ${
                  selectedCategory === cat
                    ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm'
                    : 'bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Templates Grid */}
        <div className="flex-1 overflow-y-auto pr-1 grid grid-cols-1 md:grid-cols-2 gap-3 min-h-[300px]">
          {filteredTemplates.length === 0 ? (
            <div className="col-span-2 text-center py-16 text-slate-500 text-xs">
              No SQL templates matched the selected criteria.
            </div>
          ) : (
            filteredTemplates.map((t) => (
              <div
                key={t.id}
                onClick={() => handleSelectTemplate(t)}
                className="group rounded-2xl border border-slate-800/80 bg-slate-900/40 hover:border-cyan-500/40 hover:bg-slate-900/90 p-4 flex flex-col justify-between space-y-3 cursor-pointer transition shadow-sm"
              >
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400">
                      {t.category}
                    </span>
                    <button
                      onClick={(e) => toggleFavorite(t.id, e)}
                      title={favorites.includes(t.id) ? 'Remove favorite' : 'Add to favorites'}
                      className="text-slate-500 hover:text-amber-400 transition"
                    >
                      <Star
                        size={14}
                        className={favorites.includes(t.id) ? 'fill-amber-400 text-amber-400' : ''}
                      />
                    </button>
                  </div>
                  <h4 className="text-xs font-bold text-slate-100 group-hover:text-cyan-200 transition">
                    {t.title}
                  </h4>
                  <p className="text-[11px] text-slate-400 leading-snug">{t.description}</p>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-slate-800/60 text-[11px]">
                  <span className="text-[10px] text-slate-500 font-mono">
                    {t.requiresConfig ? 'Interactive Parameters' : 'Direct Insert'}
                  </span>
                  <span className="inline-flex items-center gap-1 text-cyan-400 font-semibold text-xs group-hover:translate-x-0.5 transition">
                    {t.requiresConfig ? 'Configure' : 'Insert SQL'}
                    <ChevronRight size={13} />
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-slate-800 text-xs text-slate-500">
          <span>All templates are strictly optimized for SQLite sandbox execution.</span>
          <button
            onClick={onClose}
            className="rounded-xl px-4 py-2 font-semibold text-slate-400 hover:bg-slate-800 transition"
          >
            Close
          </button>
        </div>
      </div>

      {/* Parameter Configuration Drawer Modal */}
      {configuringTemplate && (
        <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-100">
          <div className="glass rounded-3xl border border-cyan-500/40 bg-slate-950 p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400">
                  Configure Template Parameters
                </span>
                <h4 className="text-base font-bold text-slate-100 mt-0.5">
                  {configuringTemplate.title}
                </h4>
              </div>
              <button
                onClick={() => setConfiguringTemplate(null)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X size={16} />
              </button>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              Select actual dataset columns and values to substitute into the query statement:
            </p>

            <div className="space-y-3.5 text-xs">
              {configuringTemplate.configFields?.map((f) => {
                const columnOptions =
                  f.type === 'numeric_column'
                    ? numericCols
                    : f.type === 'categorical_column'
                    ? categoricalCols
                    : f.type === 'date_column'
                    ? dateCols
                    : schemaColumns

                return (
                  <div key={f.key} className="space-y-1">
                    <label className="text-[11px] font-semibold text-slate-300">{f.label}</label>
                    {f.type.includes('column') ? (
                      <select
                        value={configParams[f.key] || ''}
                        onChange={(e) =>
                          setConfigParams((prev) => ({ ...prev, [f.key]: e.target.value }))
                        }
                        className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-cyan-400 focus:outline-none"
                      >
                        {columnOptions.map((c) => (
                          <option key={c.name} value={c.name}>
                            {c.name} ({c.type})
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type={f.type === 'number' ? 'number' : 'text'}
                        value={configParams[f.key] ?? ''}
                        onChange={(e) =>
                          setConfigParams((prev) => ({
                            ...prev,
                            [f.key]: f.type === 'number' ? Number(e.target.value) : e.target.value,
                          }))
                        }
                        className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-cyan-400 focus:outline-none"
                      />
                    )}
                  </div>
                )
              })}
            </div>

            {/* Generated Query Preview */}
            <div className="space-y-1.5 pt-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                SQL Preview with Chosen Schema:
              </span>
              <pre className="p-3 rounded-xl bg-slate-900 text-cyan-300 font-mono text-[11px] overflow-x-auto max-h-32 border border-slate-800">
                {configuringTemplate.generateQuery(configParams)}
              </pre>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setConfiguringTemplate(null)}
                className="rounded-xl px-4 py-2 text-xs font-semibold text-slate-400 hover:bg-slate-800 transition"
              >
                Back
              </button>
              <button
                type="button"
                onClick={handleApplyConfig}
                className="inline-flex items-center gap-1.5 rounded-xl bg-cyan-400 px-4 py-2 text-xs font-bold text-slate-950 hover:bg-cyan-300 transition shadow-sm"
              >
                <Check size={13} />
                Insert Query into Editor
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
