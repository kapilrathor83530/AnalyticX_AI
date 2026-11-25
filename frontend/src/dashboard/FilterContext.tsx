import { createContext, useContext, useMemo, useState } from 'react'

export interface DashboardFilter {
  column: string
  op: 'eq' | 'in' | 'not_in' | 'gte' | 'lte' | 'between' | 'contains' | 'not_contains' | 'top_n' | 'bottom_n'
  value: unknown
}

interface FilterContextValue {
  filters: DashboardFilter[]
  addFilter: (filter: DashboardFilter) => void
  removeFilter: (column: string) => void
  clearFilters: () => void
}

const FilterContext = createContext<FilterContextValue | null>(null)

export function DashboardFilterProvider({ children, initialFilters = [], onChange }: { children: React.ReactNode; initialFilters?: DashboardFilter[]; onChange?: (filters: DashboardFilter[]) => void }) {
  const [filters, setFilters] = useState<DashboardFilter[]>(initialFilters)
  const update = (next: DashboardFilter[]) => { setFilters(next); onChange?.(next) }

  const value = useMemo(
    () => ({
      filters,
      addFilter: (filter: DashboardFilter) =>
        update([...filters.filter((f) => f.column !== filter.column), filter]),
      removeFilter: (column: string) => update(filters.filter((f) => f.column !== column)),
      clearFilters: () => update([]),
    }),
    [filters],
  )

  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>
}

export function useDashboardFilters() {
  const ctx = useContext(FilterContext)
  if (!ctx) throw new Error('useDashboardFilters must be used inside DashboardFilterProvider')
  return ctx
}
