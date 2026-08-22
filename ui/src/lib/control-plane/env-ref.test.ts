import { describe, it, expect } from 'vitest'
import {
  ENV_REF_LENGTH,
  ENV_REF_PATTERN,
  environmentRefLookupFilter,
  environmentRouteRef,
  generateEnvironmentRef,
  isValidEnvironmentRef,
} from './env-ref'

describe('generateEnvironmentRef', () => {
  it('returns a 20-char lowercase alphanumeric ref', () => {
    const seen = new Set<string>()
    for (let i = 0; i < 20; i++) {
      const ref = generateEnvironmentRef()
      expect(ref.length).toBe(ENV_REF_LENGTH)
      expect(ref).toMatch(ENV_REF_PATTERN)
      seen.add(ref)
    }
    expect(seen.size).toBe(20)
  })
})

describe('environmentRouteRef', () => {
  it('prefers ref over id', () => {
    expect(
      environmentRouteRef({ ref: 'abc123def456ghi789jk', id: 'uuid-1' }),
    ).toBe('abc123def456ghi789jk')
  })

  it('falls back to id when ref is missing', () => {
    expect(environmentRouteRef({ id: 'uuid-1' })).toBe('uuid-1')
  })
})

describe('environmentRefLookupFilter', () => {
  it('looks up by ref when ref is valid', () => {
    expect(environmentRefLookupFilter('abc123def456ghi789jk')).toBe(
      'ref = "abc123def456ghi789jk"',
    )
  })

  it('falls back to id lookup for legacy segments', () => {
    expect(environmentRefLookupFilter('uuid-1')).toBe(
      'ref = "uuid-1" || id = "uuid-1"',
    )
  })
})

describe('isValidEnvironmentRef', () => {
  it('validates ref pattern', () => {
    expect(isValidEnvironmentRef(generateEnvironmentRef())).toBe(true)
    expect(isValidEnvironmentRef('production')).toBe(false)
  })
})
