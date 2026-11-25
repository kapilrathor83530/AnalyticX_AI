import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import NaturalLanguageSQLBar from '../sql-studio/NaturalLanguageSQLBar'
import AIQueryPreviewCard from '../sql-studio/AIQueryPreviewCard'
import type { SQLGenerationResponse } from '../../services/sqlStudioService'

describe('SQL Studio AI Components', () => {
  it('renders NaturalLanguageSQLBar with prompt input and trigger button', () => {
    const handleGenerate = vi.fn()
    const handleSelectSuggestion = vi.fn()

    render(
      <NaturalLanguageSQLBar
        prompt="show top 10 products by sales"
        setPrompt={vi.fn()}
        onGenerate={handleGenerate}
        loading={false}
        autoSuggest={false}
        setAutoSuggest={vi.fn()}
        suggestions={[
          {
            title: 'Top 10 Categories',
            prompt: 'top 10 categories',
            category: 'Ranking',
            sql: 'SELECT "Category" FROM dataset LIMIT 10;',
          },
        ]}
        onSelectSuggestion={handleSelectSuggestion}
      />
    )

    expect(screen.getByLabelText(/describe what you want to query/i)).toBeInTheDocument()
    expect(screen.getByText('Generate SQL')).toBeInTheDocument()
    expect(screen.getByText('Top 10 Categories')).toBeInTheDocument()

    const btn = screen.getByText('Generate SQL')
    fireEvent.click(btn)
    expect(handleGenerate).toHaveBeenCalled()
  })

  it('renders AIQueryPreviewCard with actions and does not auto-execute', () => {
    const handleInsert = vi.fn()
    const handleExplain = vi.fn()
    const handleClear = vi.fn()

    const mockPreview: SQLGenerationResponse = {
      success: true,
      sql: 'SELECT "Category", SUM("Sales") FROM dataset GROUP BY 1 LIMIT 10;',
      explanation: 'Calculates total sales grouped by category.',
      tables_used: ['dataset'],
      columns_used: ['Category', 'Sales'],
      query_type: 'ranking',
      assumptions: ['Grouped by Category'],
      warnings: [],
      is_ambiguous: false,
      clarifying_questions: [],
    }

    render(
      <AIQueryPreviewCard
        preview={mockPreview}
        onInsert={handleInsert}
        onExplain={handleExplain}
        onClear={handleClear}
      />
    )

    expect(screen.getByText(/AI Generated Query Suggestion/i)).toBeInTheDocument()
    expect(screen.getByText(/Calculates total sales grouped by category/i)).toBeInTheDocument()
    expect(screen.getByText('Replace in Editor')).toBeInTheDocument()
    expect(screen.getByText('Append to Editor')).toBeInTheDocument()
    expect(screen.getByText('Explain Query')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Replace in Editor'))
    expect(handleInsert).toHaveBeenCalledWith(mockPreview.sql, 'replace')
  })
})
