import { describe, expect, it } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { LiveApplicationProvider, useLiveApplicationContext } from '../LiveApplicationContext'
import React from 'react'

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <MemoryRouter initialEntries={['/data-prep/42']}>
      <LiveApplicationProvider>{children}</LiveApplicationProvider>
    </MemoryRouter>
  )
}

describe('LiveApplicationContext', () => {
  it('initializes with route-inferred screen state', () => {
    const { result } = renderHook(() => useLiveApplicationContext(), { wrapper })

    expect(result.current.state.screen.route).toBe('/data-prep/42')
    expect(result.current.state.screen.screenName).toBe('Data Preparation & Automated EDA Studio')
  })

  it('updates active dataset and active file', () => {
    const { result } = renderHook(() => useLiveApplicationContext(), { wrapper })

    act(() => {
      result.current.setActiveDataset({
        datasetId: 42,
        datasetName: 'Quarterly_Sales.csv',
        rowCount: 1250,
        columnCount: 14,
        qualityScore: 92.5,
        focusedColumn: 'profit',
      })
      result.current.setActiveFile({
        fileId: '42',
        fileName: 'Quarterly_Sales.csv',
        fileType: 'csv',
      })
    })

    expect(result.current.state.dataset.datasetName).toBe('Quarterly_Sales.csv')
    expect(result.current.state.dataset.rowCount).toBe(1250)
    expect(result.current.state.dataset.focusedColumn).toBe('profit')
    expect(result.current.state.file.fileName).toBe('Quarterly_Sales.csv')
  })

  it('records recent activity actions', () => {
    const { result } = renderHook(() => useLiveApplicationContext(), { wrapper })

    act(() => {
      result.current.recordAction('Removed 14 duplicate rows')
    })

    expect(result.current.state.activity.recentActions.length).toBeGreaterThan(0)
    expect(result.current.state.activity.recentActions[0].action).toBe('Removed 14 duplicate rows')
  })
})
