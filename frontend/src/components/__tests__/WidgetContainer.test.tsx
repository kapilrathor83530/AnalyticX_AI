import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import WidgetContainer from '../../dashboard/WidgetContainer'
import { DashboardFilterProvider } from '../../dashboard/FilterContext'

vi.mock('../../visualization-studio/ChartRenderer', () => ({
  default: () => <div data-testid="chart-mock" />,
}))

const widget = {
  id: 1,
  dashboard_id: 1,
  chart_type: 'bar',
  title: 'Revenue by Region',
  config: {},
  data_mapping: { x: 'region', y: 'revenue' },
  position: { x: 0, y: 0 },
  size: { w: 6, h: 4 },
  created_at: '',
}

describe('WidgetContainer', () => {
  it('renders the widget title and chart', () => {
    render(
      <DashboardFilterProvider>
        <WidgetContainer widget={widget} datasetId={1} onConfigure={() => {}} onDelete={() => {}} />
      </DashboardFilterProvider>,
    )
    expect(screen.getByText('Revenue by Region')).toBeInTheDocument()
    expect(screen.getByTestId('chart-mock')).toBeInTheDocument()
  })
})
