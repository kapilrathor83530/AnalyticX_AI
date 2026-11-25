import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { LiveApplicationProvider } from '../../contexts/LiveApplicationContext'
import UniversalCopilotModal from '../UniversalCopilotModal'
import React from 'react'

vi.mock('../../services/copilotService', () => ({
  copilotService: {
    getLanguages: vi.fn().mockResolvedValue([
      { code: 'auto', name: 'Auto-Detect', script: 'Any', native: 'Auto' },
      { code: 'hinglish', name: 'Hinglish', script: 'Latin', native: 'Hinglish' },
      { code: 'hi', name: 'Hindi', script: 'Devanagari', native: 'हिन्दी' },
    ]),
    chatWithCopilot: vi.fn().mockResolvedValue({
      answer: 'Test answer',
      detected_language: 'hinglish',
      language_name: 'Hinglish',
      script: 'Latin',
      citations: [],
      verified_facts: [],
      business_insights: [],
      suggested_questions: [],
      executed_action: null,
      tools_used: [],
      available: true,
      model: 'test',
    }),
  },
}))

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <MemoryRouter initialEntries={['/workspace']}>
      <LiveApplicationProvider>{ui}</LiveApplicationProvider>
    </MemoryRouter>
  )
}

describe('UniversalCopilotModal', () => {
  it('renders correctly when open', () => {
    renderWithProviders(
      <UniversalCopilotModal
        isOpen={true}
        onClose={() => {}}
        context={{
          dataset_name: 'Test Dataset',
          workspace_mode: 'data_prep',
        }}
      />
    )

    expect(screen.getByText('Analyticx Copilot')).toBeDefined()
    expect(screen.getByText('Test Dataset')).toBeDefined()
    expect(screen.getByPlaceholderText(/Ask about current screen, dataset/i)).toBeDefined()
    expect(screen.getByText('Explain Screen')).toBeDefined()
    expect(screen.getByText('Visual Snapshot')).toBeDefined()
  })

  it('does not render when isOpen is false', () => {
    const { container } = renderWithProviders(
      <UniversalCopilotModal
        isOpen={false}
        onClose={() => {}}
      />
    )
    expect(container.firstChild).toBeNull()
  })
})
