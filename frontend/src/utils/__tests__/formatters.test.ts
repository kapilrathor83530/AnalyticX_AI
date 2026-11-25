import { describe, expect, it } from 'vitest'
import { formatBytes, formatNumber, formatPercent } from '../formatters'

describe('formatters', () => {
  it('formats numbers', () => {
    expect(formatNumber(1234.5)).toBe('1,234.50')
    expect(formatNumber(null)).toBe('—')
  })

  it('formats percentages', () => {
    expect(formatPercent(12.345)).toBe('12.35%')
    expect(formatPercent(undefined)).toBe('—')
  })

  it('formats bytes', () => {
    expect(formatBytes(500)).toBe('500 B')
    expect(formatBytes(2048)).toBe('2.0 KB')
    expect(formatBytes(2 * 1024 * 1024)).toBe('2.00 MB')
  })
})
