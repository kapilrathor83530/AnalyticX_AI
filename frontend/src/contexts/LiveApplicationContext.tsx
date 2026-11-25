import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { api } from '../api/client'

export interface ScreenState {
  route: string
  screenName: string
  screenDescription?: string
}

export interface ActiveFileState {
  fileId?: string | number | null
  fileName?: string | null
  fileType?: 'csv' | 'excel' | 'pdf' | 'extracted_table' | 'report' | null
  pdfPageNumber?: number | null
  pdfTotalPages?: number | null
  selectedPdfText?: string | null
}

export interface ActiveDatasetState {
  datasetId?: number | null
  datasetName?: string | null
  version: number
  rowCount: number
  columnCount: number
  qualityScore?: number | null
  selectedColumns: string[]
  focusedColumn?: string | null
  focusedColumnStats?: Record<string, unknown> | null
  pendingDecisionsCount: number
  lastCleaningAction?: string | null
}

export interface ActiveDashboardState {
  dashboardId?: number | null
  dashboardName?: string | null
  selectedWidgetId?: number | null
  selectedChartType?: string | null
  selectedChartTitle?: string | null
  activeMeasures: string[]
  activeDimensions: string[]
  activeFilters: Record<string, unknown>
  widgetsCount: number
}

export interface ActivityState {
  recentActions: Array<{ id: string; action: string; timestamp: string }>
  taskStatus: 'idle' | 'running' | 'completed' | 'failed'
  hasUnsavedChanges: boolean
}

export interface VisualSnapshotState {
  hasSnapshot: boolean
  snapshotTimestamp?: string | null
  domSummary?: string | null
  imageUri?: string | null
}

export interface LiveApplicationState {
  workspaceId: string
  workspaceName: string
  screen: ScreenState
  file: ActiveFileState
  dataset: ActiveDatasetState
  dashboard: ActiveDashboardState
  activity: ActivityState
  visual: VisualSnapshotState
  languagePreference: string
}

export interface ScreenExplanationResponse {
  screen_summary: string
  active_file_summary?: string
  analysis_status: string
  recommended_next_steps: string[]
  key_observations: string[]
  warnings_or_issues: string[]
  detected_language: string
  language_name: string
  is_visual_analysis: boolean
}

export interface VisualAnalysisResponse {
  explanation: string
  visual_elements_detected: string[]
  layout_health: string
  numerical_grounding_note: string
  suggested_actions: string[]
}

interface LiveApplicationContextValue {
  state: LiveApplicationState
  setScreen: (screen: Partial<ScreenState>) => void
  setActiveFile: (file: Partial<ActiveFileState>) => void
  setActiveDataset: (dataset: Partial<ActiveDatasetState>) => void
  setActiveDashboard: (dashboard: Partial<ActiveDashboardState>) => void
  recordAction: (actionText: string) => void
  setTaskStatus: (status: 'idle' | 'running' | 'completed' | 'failed') => void
  setLanguagePreference: (lang: string) => void
  captureScreenSnapshot: () => Promise<{ domSummary: string; imageUri?: string }>
  explainCurrentScreen: (question?: string, lang?: string) => Promise<ScreenExplanationResponse>
  analyzeVisualWorkspace: () => Promise<VisualAnalysisResponse>
}

const defaultState: LiveApplicationState = {
  workspaceId: 'default',
  workspaceName: 'Analyticx Workspace',
  screen: {
    route: '/',
    screenName: 'Overview',
    screenDescription: 'Main Analyticx AI workspace dashboard',
  },
  file: {},
  dataset: {
    version: 1,
    rowCount: 0,
    columnCount: 0,
    selectedColumns: [],
    pendingDecisionsCount: 0,
  },
  dashboard: {
    activeMeasures: [],
    activeDimensions: [],
    activeFilters: {},
    widgetsCount: 0,
  },
  activity: {
    recentActions: [],
    taskStatus: 'idle',
    hasUnsavedChanges: false,
  },
  visual: {
    hasSnapshot: false,
  },
  languagePreference: 'auto',
}

const LiveApplicationContext = createContext<LiveApplicationContextValue | null>(null)

export function LiveApplicationProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<LiveApplicationState>(defaultState)
  const location = useLocation()

  // Auto-detect route changes and configure screen title
  useEffect(() => {
    const path = location.pathname
    let screenName = 'Analytics Workspace'
    let description = 'General analytics overview'

    if (path.startsWith('/data-prep') || path.startsWith('/data-studio')) {
      screenName = 'Data Preparation & Automated EDA Studio'
      description = 'Profile data quality, clean records reversibly, and inspect evidence-based EDA charts'
    } else if (path.startsWith('/workspace') || path.startsWith('/upload')) {
      screenName = 'Data Upload Center'
      description = 'Upload and register CSV, Excel, and PDF files'
    } else if (path.startsWith('/dashboards')) {
      screenName = 'Interactive Dashboard Studio'
      description = 'Explore interactive multi-visual dashboards and customize charts'
    } else if (path.startsWith('/models')) {
      screenName = 'Model Management Center'
      description = 'Manage local open-weight LLMs and Ollama connection status'
    } else if (path.startsWith('/health')) {
      screenName = 'System Health & Telemetry'
      description = 'Monitor hardware, database latency, and service availability'
    } else if (path.startsWith('/forecasting')) {
      screenName = 'Forecasting Center'
      description = 'Time-series forecasting with trend trajectory modeling'
    } else if (path.startsWith('/scenarios')) {
      screenName = 'Decision Simulator'
      description = 'What-if simulations and business sensitivity models'
    }

    setState((prev) => ({
      ...prev,
      screen: {
        route: path,
        screenName,
        screenDescription: description,
      },
    }))
  }, [location.pathname])

  const setScreen = useCallback((screen: Partial<ScreenState>) => {
    setState((prev) => ({
      ...prev,
      screen: { ...prev.screen, ...screen },
    }))
  }, [])

  const setActiveFile = useCallback((file: Partial<ActiveFileState>) => {
    setState((prev) => ({
      ...prev,
      file: { ...prev.file, ...file },
    }))
  }, [])

  const setActiveDataset = useCallback((dataset: Partial<ActiveDatasetState>) => {
    setState((prev) => ({
      ...prev,
      dataset: { ...prev.dataset, ...dataset },
    }))
  }, [])

  const setActiveDashboard = useCallback((dashboard: Partial<ActiveDashboardState>) => {
    setState((prev) => ({
      ...prev,
      dashboard: { ...prev.dashboard, ...dashboard },
    }))
  }, [])

  const recordAction = useCallback((actionText: string) => {
    setState((prev) => {
      const entry = {
        id: `act_${Date.now()}`,
        action: actionText,
        timestamp: new Date().toISOString(),
      }
      return {
        ...prev,
        activity: {
          ...prev.activity,
          recentActions: [entry, ...prev.activity.recentActions.slice(0, 9)],
        },
      }
    })
  }, [])

  const setTaskStatus = useCallback((status: 'idle' | 'running' | 'completed' | 'failed') => {
    setState((prev) => ({
      ...prev,
      activity: { ...prev.activity, taskStatus: status },
    }))
  }, [])

  const setLanguagePreference = useCallback((lang: string) => {
    setState((prev) => ({
      ...prev,
      languagePreference: lang,
    }))
  }, [])

  // Captures structured DOM summary and visual canvas snapshot
  const captureScreenSnapshot = useCallback(async () => {
    const rootEl = document.getElementById('root') || document.body

    // Extract visible headings, cards, and metric pills
    const headings = Array.from(rootEl.querySelectorAll('h1, h2, h3, h4'))
      .map((h) => (h.textContent || '').trim())
      .filter((t) => t.length > 0)
      .slice(0, 8)

    const buttons = Array.from(rootEl.querySelectorAll('button'))
      .map((b) => (b.textContent || '').trim())
      .filter((t) => t.length > 0 && t.length < 25)
      .slice(0, 10)

    const domSummary = `Screen '${state.screen.screenName}' [Route: ${state.screen.route}]. Headings: ${headings.join(' | ')}. Interactive controls: ${buttons.join(', ')}.`

    // Optional visual canvas capture (lightweight synthetic representation)
    let imageUri: string | undefined = undefined
    try {
      const canvas = document.createElement('canvas')
      canvas.width = 480
      canvas.height = 300
      const ctx = canvas.getContext('2d')
      if (ctx) {
        ctx.fillStyle = '#020617'
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        ctx.fillStyle = '#06b6d4'
        ctx.font = '16px sans-serif'
        ctx.fillText(`Analyticx AI Workspace: ${state.screen.screenName}`, 20, 40)
        ctx.fillStyle = '#94a3b8'
        ctx.font = '12px sans-serif'
        ctx.fillText(`Route: ${state.screen.route}`, 20, 70)
        if (state.dataset.datasetName) {
          ctx.fillText(`Dataset: ${state.dataset.datasetName} (${state.dataset.rowCount} rows)`, 20, 100)
        }
        if (state.dashboard.dashboardName) {
          ctx.fillText(`Dashboard: ${state.dashboard.dashboardName}`, 20, 130)
        }
        imageUri = canvas.toDataURL('image/png')
      }
    } catch {
      // Non-blocking
    }

    setState((prev) => ({
      ...prev,
      visual: {
        hasSnapshot: true,
        snapshotTimestamp: new Date().toISOString(),
        domSummary,
        imageUri,
      },
    }))

    return { domSummary, imageUri }
  }, [state.screen, state.dataset, state.dashboard])

  const explainCurrentScreen = useCallback(
    async (question?: string, lang?: string) => {
      const payload = {
        question: question || 'What does the current screen show and what should I do next?',
        context: {
          workspace_id: state.workspaceId,
          workspace_name: state.workspaceName,
          screen: state.screen,
          file: state.file,
          dataset: {
            ...state.dataset,
            dataset_id: state.dataset.datasetId,
            dataset_name: state.dataset.datasetName,
            row_count: state.dataset.rowCount,
            column_count: state.dataset.columnCount,
            quality_score: state.dataset.qualityScore,
            focused_column: state.dataset.focusedColumn,
            pending_decisions_count: state.dataset.pendingDecisionsCount,
          },
          dashboard: {
            ...state.dashboard,
            dashboard_id: state.dashboard.dashboardId,
            dashboard_name: state.dashboard.dashboardName,
            selected_widget_id: state.dashboard.selectedWidgetId,
            selected_chart_type: state.dashboard.selectedChartType,
            selected_chart_title: state.dashboard.selectedChartTitle,
            active_measures: state.dashboard.activeMeasures,
            active_filters: state.dashboard.activeFilters,
            widgets_count: state.dashboard.widgetsCount,
          },
          activity: state.activity,
          visual: state.visual,
          language_preference: lang || state.languagePreference,
        },
        language: lang || state.languagePreference,
        use_llm: true,
      }

      const res = await api.post<ScreenExplanationResponse>('/context/explain-screen', payload)
      return res.data
    },
    [state]
  )

  const analyzeVisualWorkspace = useCallback(async () => {
    const snap = await captureScreenSnapshot()
    const payload = {
      image_base64: snap.imageUri,
      context: {
        workspace_id: state.workspaceId,
        workspace_name: state.workspaceName,
        screen: state.screen,
        file: state.file,
        dataset: state.dataset,
        dashboard: state.dashboard,
        activity: state.activity,
        visual: {
          has_snapshot: true,
          snapshot_timestamp: new Date().toISOString(),
          dom_summary: snap.domSummary,
          image_base64: snap.imageUri,
        },
        language_preference: state.languagePreference,
      },
      query: 'Analyze what is visible on this screen and check layout health',
      language: state.languagePreference,
    }

    const res = await api.post<VisualAnalysisResponse>('/context/visual-analysis', payload)
    return res.data
  }, [state, captureScreenSnapshot])

  return (
    <LiveApplicationContext.Provider
      value={{
        state,
        setScreen,
        setActiveFile,
        setActiveDataset,
        setActiveDashboard,
        recordAction,
        setTaskStatus,
        setLanguagePreference,
        captureScreenSnapshot,
        explainCurrentScreen,
        analyzeVisualWorkspace,
      }}
    >
      {children}
    </LiveApplicationContext.Provider>
  )
}

export function useLiveApplicationContext() {
  const context = useContext(LiveApplicationContext)
  if (!context) {
    throw new Error('useLiveApplicationContext must be used within a LiveApplicationProvider')
  }
  return context
}
