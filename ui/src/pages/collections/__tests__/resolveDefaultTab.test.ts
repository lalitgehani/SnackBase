import { describe, it, expect } from 'vitest'
import { resolveDefaultTab } from '../defaultTab'

describe('resolveDefaultTab', () => {
  it('returns data when records_count > 0', () => {
    expect(resolveDefaultTab(1)).toBe('data')
    expect(resolveDefaultTab(100)).toBe('data')
  })

  it('returns schema when records_count is 0', () => {
    expect(resolveDefaultTab(0)).toBe('schema')
  })
})
