import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ChartRenderer from '../ChartRenderer'

vi.mock('react-plotly.js', () => ({
  default: ({ data, layout }: { data: Array<Record<string, unknown>>; layout?: Record<string, unknown> }) => (
    <div data-testid="plotly-mock" data-trace-type={String(data?.[0]?.type || '')} data-orientation={String(data?.[0]?.orientation || '')}>
      {String((layout?.title as Record<string, unknown> | undefined)?.text || '')}
    </div>
  ),
}))

const mockRenderChart = vi.fn()
vi.mock('../../services/dashboardService', () => ({
  dashboardService: {
    renderChart: (...args: unknown[]) => mockRenderChart(...args),
  },
}))

describe('ChartRenderer Universal Visualization Integration', () => {
  it('renders horizontal_bar and displays sampled dataset badge + warnings', async () => {
    mockRenderChart.mockResolvedValueOnce({
      chart_type: 'horizontal_bar',
      data: [{ department: 'Engineering', salary: 120000 }],
      layout: { title: 'Salary by Dept' },
      warnings: ['Top 10 categories displayed'],
      metadata: { sampled: true, original_rows: 10000 },
    })

    render(
      <ChartRenderer
        datasetId={1}
        chartType="horizontal_bar"
        dataMapping={{ x: 'department', y: 'salary' }}
        title="Salary by Dept"
      />,
    )

    await waitFor(() => {
      expect(screen.getByTestId('plotly-mock')).toBeInTheDocument()
    })
    expect(screen.getByTestId('plotly-mock')).toHaveAttribute('data-orientation', 'h')
    expect(screen.getByText(/Sampled view/i)).toBeInTheDocument()
    expect(screen.getByText('Top 10 categories displayed')).toBeInTheDocument()
  })

  it('shows validation error and suggested_alternative when backend rejects invalid visual', async () => {
    mockRenderChart.mockResolvedValueOnce({
      chart_type: 'pie',
      data: [],
      layout: {},
      warnings: [],
      error: 'Pie chart exceeds 15 unique categories',
      suggested_alternative: 'horizontal_bar',
      metadata: { validation_passed: false },
    })

    render(
      <ChartRenderer
        datasetId={1}
        chartType="pie"
        dataMapping={{ labels: 'vendor', values: 'spend' }}
      />,
    )

    await waitFor(() => {
      expect(screen.getByText('Pie chart exceeds 15 unique categories')).toBeInTheDocument()
    })
    expect(screen.getByText('horizontal_bar')).toBeInTheDocument()
  })

  it('renders correlation_matrix without requiring explicit x/y mapping', async () => {
    mockRenderChart.mockResolvedValueOnce({
      chart_type: 'correlation_matrix',
      data: [
        { x: 'revenue', y: 'revenue', value: 1 },
        { x: 'revenue', y: 'profit', value: 0.92 },
      ],
      layout: { title: 'Correlation Matrix' },
      warnings: [],
      metadata: {},
    })

    render(
      <ChartRenderer
        datasetId={1}
        chartType="correlation_matrix"
        dataMapping={{}}
        title="Correlation Matrix"
      />,
    )

    await waitFor(() => {
      expect(screen.getByTestId('plotly-mock')).toBeInTheDocument()
    })
    expect(screen.getByTestId('plotly-mock')).toHaveAttribute('data-trace-type', 'heatmap')
  })
})
