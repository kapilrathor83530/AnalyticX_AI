import type { ChartTypeDefinition } from '../types/chart'

export const chartCategoryLabels: Record<string, string> = {
  comparison: 'Comparison',
  trend: 'Trend',
  composition: 'Composition',
  statistical: 'Statistical',
  business: 'Business',
}

export function groupChartsByCategory(charts: ChartTypeDefinition[]) {
  const groups: Record<string, ChartTypeDefinition[]> = {}
  for (const chart of charts) {
    if (!groups[chart.category]) groups[chart.category] = []
    groups[chart.category].push(chart)
  }
  return groups
}
