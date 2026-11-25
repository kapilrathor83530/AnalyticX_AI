import { useCallback, useState } from 'react'
import type { Widget } from '../types/dashboard'

interface HistoryState {
  past: Widget[][]
  present: Widget[]
  future: Widget[][]
}

export function useDashboardHistory(initial: Widget[] = []) {
  const [state, setState] = useState<HistoryState>({ past: [], present: initial, future: [] })

  const set = useCallback((next: Widget[]) => {
    setState((s) => ({
      past: [...s.past, s.present],
      present: next,
      future: [],
    }))
  }, [])

  const undo = useCallback(() => {
    setState((s) => {
      if (s.past.length === 0) return s
      const previous = s.past[s.past.length - 1]
      return {
        past: s.past.slice(0, -1),
        present: previous,
        future: [s.present, ...s.future],
      }
    })
  }, [])

  const redo = useCallback(() => {
    setState((s) => {
      if (s.future.length === 0) return s
      const next = s.future[0]
      return {
        past: [...s.past, s.present],
        present: next,
        future: s.future.slice(1),
      }
    })
  }, [])

  return {
    widgets: state.present,
    set,
    undo,
    redo,
    canUndo: state.past.length > 0,
    canRedo: state.future.length > 0,
  }
}
