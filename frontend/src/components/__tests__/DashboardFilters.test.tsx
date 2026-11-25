import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import DashboardFilters from '../../dashboard/DashboardFilters'
import { DashboardFilterProvider } from '../../dashboard/FilterContext'

describe('DashboardFilters', () => {
  it('applies a filter', () => {
    render(
      <DashboardFilterProvider>
        <DashboardFilters columns={['region']} valuesByColumn={{ region: ['North', 'South'] }} />
      </DashboardFilterProvider>,
    )
    const selects = screen.getAllByRole('combobox')
    fireEvent.change(selects[1], { target: { value: 'North' } })
    expect(screen.getByText(/region = North/)).toBeInTheDocument()
  })
})
