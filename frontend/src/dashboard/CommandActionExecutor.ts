import { dashboardService } from '../services/dashboardService'
import type { CommandResponse } from '../types/llm'
import type { Widget } from '../types/dashboard'

interface ApplyResult {
  applied: boolean
  widgets: Widget[]
  message: string
}

export async function applyCommand(
  dashboardId: number,
  datasetId: number,
  command: CommandResponse,
  widgets: Widget[],
): Promise<ApplyResult> {
  if (!command.available) {
    return { applied: false, widgets, message: 'LLM unavailable' }
  }

  if (command.clarification_needed) {
    return {
      applied: false,
      widgets,
      message: command.clarification_question || 'Clarification needed',
    }
  }

  if (command.action === 'add_chart' && command.chart_type) {
    const created = await dashboardService.addWidget(dashboardId, {
      chart_type: command.chart_type,
      title: command.chart_type + ' chart',
      config: { appearance: { color: '#22d3ee', legend: true }, aggregation: 'sum' },
      data_mapping: command.data_mapping,
      position: { x: 0, y: Infinity as unknown as number },
      size: { w: 6, h: 4 },
    })
    return { applied: true, widgets: [...widgets, created], message: 'Chart added' }
  }

  if (command.action === 'change_chart_type' && command.chart_type) {
    const target = widgets[widgets.length - 1]
    if (!target) return { applied: false, widgets, message: 'No widget to change' }
    const updated = await dashboardService.updateWidget(dashboardId, target.id, {
      chart_type: command.chart_type,
    })
    return {
      applied: true,
      widgets: widgets.map((w) => (w.id === target.id ? updated : w)),
      message: `Changed to ${command.chart_type}`,
    }
  }

  if (command.action === 'filter' && command.value) {
    return { applied: false, widgets, message: 'Filter action not yet auto-applied.' }
  }

  return { applied: false, widgets, message: 'Command not yet supported for auto-apply.' }
}
