import {
  Code,
  Database,
  Hash,
  Sparkles,
  Type,
  Variable,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { SchemaColumn } from '../../services/sqlStudioService'

interface AutocompleteItem {
  label: string
  insertText: string
  type: 'keyword' | 'column' | 'table' | 'function' | 'operator'
  subtext?: string
}

const SQL_KEYWORDS = [
  'SELECT',
  'FROM',
  'WHERE',
  'GROUP BY',
  'ORDER BY',
  'HAVING',
  'LIMIT',
  'OFFSET',
  'DISTINCT',
  'JOIN',
  'LEFT JOIN',
  'INNER JOIN',
  'ON',
  'AS',
  'CASE',
  'WHEN',
  'THEN',
  'ELSE',
  'END',
  'UNION',
  'WITH',
  'AND',
  'OR',
  'NOT',
  'IN',
  'BETWEEN',
  'LIKE',
  'IS NULL',
  'IS NOT NULL',
  'ASC',
  'DESC',
]

const SQL_FUNCTIONS = [
  { name: 'COUNT', desc: 'Counts rows: COUNT(*)' },
  { name: 'SUM', desc: 'Sums numeric values: SUM("col")' },
  { name: 'AVG', desc: 'Averages values: AVG("col")' },
  { name: 'MIN', desc: 'Minimum value: MIN("col")' },
  { name: 'MAX', desc: 'Maximum value: MAX("col")' },
  { name: 'ROUND', desc: 'Rounds float: ROUND("col", 2)' },
  { name: 'strftime', desc: "Formats date: strftime('%Y-%m', date_col)" },
  { name: 'COALESCE', desc: 'First non-null: COALESCE("col", default)' },
  { name: 'NULLIF', desc: 'Returns null if equal: NULLIF(a, b)' },
  { name: 'LOWER', desc: 'Lowercase string: LOWER("col")' },
  { name: 'UPPER', desc: 'Uppercase string: UPPER("col")' },
  { name: 'TRIM', desc: 'Trims whitespace: TRIM("col")' },
  { name: 'LENGTH', desc: 'String length: LENGTH("col")' },
  { name: 'CAST', desc: 'Casts type: CAST("col" AS INTEGER)' },
]

interface Props {
  value: string
  onChange: (val: string) => void
  schemaColumns: SchemaColumn[]
  placeholder?: string
}

export default function SQLEditorWithAutocomplete({
  value,
  onChange,
  schemaColumns,
  placeholder,
}: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [cursorPos, setCursorPos] = useState(0)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(0)

  // Extract current word at cursor
  const currentToken = useMemo(() => {
    if (!value || cursorPos === 0) return ''
    const beforeCursor = value.slice(0, cursorPos)
    const match = beforeCursor.match(/[a-zA-Z0-9_"]+$/)
    return match ? match[0].replace(/"/g, '') : ''
  }, [value, cursorPos])

  // Context preceding the cursor
  const precedingContext = useMemo(() => {
    const beforeCursor = value.slice(0, cursorPos).toUpperCase()
    if (beforeCursor.includes('SELECT') && !beforeCursor.includes('FROM')) return 'SELECT_CLAUSE'
    if (beforeCursor.includes('FROM') && !beforeCursor.includes('WHERE') && !beforeCursor.includes('GROUP') && !beforeCursor.includes('ORDER')) return 'FROM_CLAUSE'
    if (beforeCursor.includes('WHERE') && !beforeCursor.includes('GROUP') && !beforeCursor.includes('ORDER')) return 'WHERE_CLAUSE'
    if (beforeCursor.includes('GROUP BY') && !beforeCursor.includes('ORDER')) return 'GROUP_CLAUSE'
    if (beforeCursor.includes('ORDER BY')) return 'ORDER_CLAUSE'
    return 'GENERAL'
  }, [value, cursorPos])

  // Generate matching suggestions
  const suggestions = useMemo(() => {
    if (!currentToken && precedingContext === 'GENERAL') return []

    const qLower = currentToken.toLowerCase()
    const items: AutocompleteItem[] = []

    // 1. Column suggestions (higher priority in SELECT, WHERE, GROUP BY, ORDER BY)
    if (precedingContext !== 'FROM_CLAUSE') {
      schemaColumns.forEach((col) => {
        if (!currentToken || col.name.toLowerCase().includes(qLower)) {
          items.push({
            label: col.name,
            insertText: `"${col.name}"`,
            type: 'column',
            subtext: col.type,
          })
        }
      })
    }

    // 2. Table suggestions (higher priority in FROM clause)
    if (precedingContext === 'FROM_CLAUSE' || !currentToken || 'dataset'.includes(qLower)) {
      items.push({ label: 'dataset', insertText: 'dataset', type: 'table', subtext: 'Active Table' })
      items.push({ label: 'data', insertText: 'data', type: 'table', subtext: 'Alias' })
    }

    // 3. Functions
    if (precedingContext === 'SELECT_CLAUSE' || precedingContext === 'WHERE_CLAUSE' || currentToken.length > 1) {
      SQL_FUNCTIONS.forEach((fn) => {
        if (!currentToken || fn.name.toLowerCase().startsWith(qLower)) {
          items.push({
            label: fn.name,
            insertText: `${fn.name}()`,
            type: 'function',
            subtext: fn.desc,
          })
        }
      })
    }

    // 4. Keywords
    SQL_KEYWORDS.forEach((kw) => {
      if (currentToken && kw.toLowerCase().startsWith(qLower)) {
        items.push({ label: kw, insertText: kw + ' ', type: 'keyword' })
      }
    })

    return items.slice(0, 10)
  }, [currentToken, schemaColumns, precedingContext])

  useEffect(() => {
    if (suggestions.length > 0 && currentToken.length > 0) {
      setShowSuggestions(true)
      setSelectedIndex(0)
    } else {
      setShowSuggestions(false)
    }
  }, [suggestions.length, currentToken])

  const acceptSuggestion = (item: AutocompleteItem) => {
    if (!textareaRef.current) return
    const beforeCursor = value.slice(0, cursorPos)
    const afterCursor = value.slice(cursorPos)

    // Replace the partial token with the insertText
    const tokenStart = beforeCursor.length - currentToken.length
    const newText = beforeCursor.slice(0, tokenStart) + item.insertText + afterCursor
    const newCursor = tokenStart + item.insertText.length

    onChange(newText)
    setShowSuggestions(false)

    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus()
        textareaRef.current.setSelectionRange(newCursor, newCursor)
      }
    }, 0)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (showSuggestions && suggestions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex((prev) => (prev + 1) % suggestions.length)
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex((prev) => (prev - 1 + suggestions.length) % suggestions.length)
        return
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault()
        acceptSuggestion(suggestions[selectedIndex])
        return
      }
      if (e.key === 'Escape') {
        e.preventDefault()
        setShowSuggestions(false)
        return
      }
    }
  }

  const handleKeyUp = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (textareaRef.current) {
      setCursorPos(textareaRef.current.selectionStart)
    }
  }

  const lineCount = useMemo(() => {
    return Math.max(value.split('\n').length, 5)
  }, [value])

  return (
    <div className="relative rounded-2xl border border-slate-800 bg-slate-950/95 font-mono text-xs shadow-inner overflow-hidden flex">
      {/* Line Numbers */}
      <div className="select-none py-3.5 px-3 bg-slate-900/40 text-slate-600 text-right font-mono text-[11px] border-r border-slate-800/80 w-10 shrink-0">
        {Array.from({ length: lineCount }).map((_, i) => (
          <div key={i} className="leading-relaxed">
            {i + 1}
          </div>
        ))}
      </div>

      {/* Editor Surface */}
      <div className="relative flex-1">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => {
            onChange(e.target.value)
            setCursorPos(e.target.selectionStart)
          }}
          onKeyDown={handleKeyDown}
          onKeyUp={handleKeyUp}
          onClick={() => {
            if (textareaRef.current) setCursorPos(textareaRef.current.selectionStart)
          }}
          placeholder={placeholder || 'SELECT * FROM dataset LIMIT 25;'}
          className="w-full h-44 bg-transparent font-mono text-xs text-cyan-100 p-3.5 leading-relaxed focus:outline-none resize-y selection:bg-cyan-500/30"
          spellCheck={false}
        />

        {/* Floating Autocomplete Dropdown */}
        {showSuggestions && suggestions.length > 0 && (
          <div className="absolute left-6 bottom-3 z-50 w-72 rounded-xl border border-cyan-500/40 bg-slate-950/95 p-1 shadow-2xl backdrop-blur-xl animate-in fade-in zoom-in-95 duration-100 max-h-56 overflow-y-auto">
            <div className="px-2 py-1 text-[9px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-800 mb-1 flex items-center justify-between">
              <span>SQL Autocomplete & Schema</span>
              <span className="text-cyan-400 font-mono">↵ / Tab to insert</span>
            </div>

            <div className="space-y-0.5">
              {suggestions.map((item, idx) => (
                <button
                  key={idx}
                  type="button"
                  onMouseDown={(e) => {
                    e.preventDefault()
                    acceptSuggestion(item)
                  }}
                  className={`w-full text-left px-2 py-1.5 rounded-lg flex items-center justify-between text-xs transition ${
                    idx === selectedIndex
                      ? 'bg-cyan-500/20 text-cyan-200 border border-cyan-500/30 shadow-sm'
                      : 'text-slate-300 hover:bg-slate-900'
                  }`}
                >
                  <div className="flex items-center gap-1.5 truncate">
                    {item.type === 'column' ? (
                      <Variable size={12} className="text-cyan-400 shrink-0" />
                    ) : item.type === 'table' ? (
                      <Database size={12} className="text-purple-400 shrink-0" />
                    ) : item.type === 'function' ? (
                      <Hash size={12} className="text-emerald-400 shrink-0" />
                    ) : (
                      <Code size={12} className="text-blue-400 shrink-0" />
                    )}
                    <span className="font-mono font-medium truncate">{item.label}</span>
                  </div>

                  {item.subtext && (
                    <span className="text-[10px] text-slate-500 font-mono shrink-0 ml-2">
                      {item.subtext}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
