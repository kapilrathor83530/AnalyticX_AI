import { useEffect, useRef } from 'react'
import { Responsive, WidthProvider } from 'react-grid-layout'
import type { Layout } from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'

import WidgetContainer from './WidgetContainer'
import type { Widget } from '../types/dashboard'

const ResponsiveGrid = WidthProvider(Responsive)

interface Props {
  widgets: Widget[]
  datasetId: number
  columns: string[]
  valuesByColumn?: Record<string, (string | number)[]>
  onLayoutChange: (layout: Layout[]) => void
  onConfigure: (widget: Widget) => void
  onDelete: (widget: Widget) => void
  onDuplicate: (widget: Widget) => void
  onUpdate: (widget: Widget, changes: Partial<Widget>) => void
}

export default function DashboardGrid({
  widgets,
  datasetId,
  columns,
  valuesByColumn,
  onLayoutChange,
  onConfigure,
  onDelete,
  onDuplicate,
  onUpdate,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)

  // Observe container dimensions and fire resize events for react-grid-layout and plotly charts
  useEffect(() => {
    if (!containerRef.current) return
    let timeoutId: number
    const observer = new ResizeObserver(() => {
      window.clearTimeout(timeoutId)
      timeoutId = window.setTimeout(() => {
        window.dispatchEvent(new Event('resize'))
      }, 30)
    })
    observer.observe(containerRef.current)
    return () => {
      observer.disconnect()
      window.clearTimeout(timeoutId)
    }
  }, [])

  const default12 = widgets.map((widget) => ({
    i: String(widget.id),
    x: widget.position?.x ?? 0,
    y: widget.position?.y ?? 0,
    w: widget.size?.w ?? 6,
    h: widget.size?.h ?? 4,
    minW: 2,
    minH: 2,
  }))

  const layouts = {
    lg: default12,
    md: default12,
    sm: default12,
    xs: widgets.map((widget, i) => ({
      i: String(widget.id),
      x: 0,
      y: i * 4,
      w: 6,
      h: widget.size?.h ?? 4,
      minW: 2,
      minH: 2,
    })),
  }

  return (
    <div ref={containerRef} className="w-full min-w-0 transition-all duration-300">
      <ResponsiveGrid
        className="layout"
        layouts={layouts}
        breakpoints={{ lg: 1024, md: 768, sm: 640, xs: 480, xxs: 0 }}
        cols={{ lg: 12, md: 12, sm: 12, xs: 6, xxs: 2 }}
        rowHeight={60}
        draggableHandle=".widget-drag-handle"
        draggableCancel=".widget-controls, button, input, select, .visual-filter-panel"
        isResizable
        resizeHandles={['se', 'e', 's']}
        margin={[16, 16]}
        containerPadding={[0, 0]}
        onLayoutChange={(layout) => onLayoutChange(layout as Layout[])}
        compactType="vertical"
      >
        {widgets.map((widget) => (
          <div key={String(widget.id)} className="h-full w-full min-w-0">
            <WidgetContainer
              widget={widget}
              datasetId={datasetId}
              columns={columns}
              valuesByColumn={valuesByColumn}
              onConfigure={onConfigure}
              onDelete={onDelete}
              onDuplicate={onDuplicate}
              onUpdate={onUpdate}
            />
          </div>
        ))}
      </ResponsiveGrid>
    </div>
  )
}
