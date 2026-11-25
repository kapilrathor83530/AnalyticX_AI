import React, { createContext, useContext, useEffect, useState } from 'react'

export type AppMode = 'basic' | 'pro' | 'advanced'

export interface ModeConfig {
  id: AppMode
  title: string
  subtitle: string
  badge: string
  badgeColor: string
  activeTabColor: string
  iconColor: string
  goal: string
  exampleOutput: string
}

export const MODES: Record<AppMode, ModeConfig> = {
  basic: {
    id: 'basic',
    title: 'Basic Mode',
    subtitle: 'Data Cleaning & Preprocessing',
    badge: 'Clean & Prep',
    badgeColor: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
    activeTabColor: 'bg-emerald-500/20 text-emerald-200 border-emerald-500/40 shadow-emerald-950/40',
    iconColor: 'text-emerald-400',
    goal: 'Turn messy raw data into clean, analysis-ready data with automated detection and fixes.',
    exampleOutput: 'cleaned_sales_data.csv plus comprehensive data quality summary report',
  },
  pro: {
    id: 'pro',
    title: 'Pro Mode',
    subtitle: 'Exploratory Data Analysis & Visualization',
    badge: 'EDA & Visuals',
    badgeColor: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300',
    activeTabColor: 'bg-cyan-500/20 text-cyan-200 border-cyan-500/40 shadow-cyan-950/40',
    iconColor: 'text-cyan-400',
    goal: 'Interactive charts, correlation heatmaps, cross-filtered dashboards, and live SQL querying.',
    exampleOutput: 'Interactive dashboard showing sales, profit, top products, and regional performance',
  },
  advanced: {
    id: 'advanced',
    title: 'Advanced Mode',
    subtitle: 'Project Insights, BI & Automation',
    badge: 'Insights & BI',
    badgeColor: 'border-purple-500/30 bg-purple-500/10 text-purple-300',
    activeTabColor: 'bg-purple-500/20 text-purple-200 border-purple-500/40 shadow-purple-950/40',
    iconColor: 'text-purple-400',
    goal: 'Automated project EDA, proactive business insights, ANOVA hypothesis tests, AI chat, and executive PDF/Word/PPTX decks.',
    exampleOutput: 'Comprehensive project intelligence report with mathematical traces, ANOVA tests, and strategic action plans',
  },
}

interface ModeContextType {
  mode: AppMode
  setMode: (mode: AppMode) => void
  config: ModeConfig
}

const ModeContext = createContext<ModeContextType | undefined>(undefined)

export function ModeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<AppMode>(() => {
    try {
      const saved = localStorage.getItem('analyticx_active_mode') as AppMode
      if (saved && MODES[saved]) return saved
    } catch {
      // fallback
    }
    return 'basic'
  })

  function setMode(newMode: AppMode) {
    setModeState(newMode)
    try {
      localStorage.setItem('analyticx_active_mode', newMode)
    } catch {
      // ignore
    }
  }

  const config = MODES[mode]

  return (
    <ModeContext.Provider value={{ mode, setMode, config }}>
      {children}
    </ModeContext.Provider>
  )
}

export function useAppMode() {
  const context = useContext(ModeContext)
  if (!context) {
    throw new Error('useAppMode must be used within a ModeProvider')
  }
  return context
}
