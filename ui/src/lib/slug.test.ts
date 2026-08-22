import { describe, it, expect } from 'vitest'
import { isValidSlug, slugifyName, SLUG_REGEX } from './slug'

describe('slug utilities', () => {
  it('accepts valid slugs', () => {
    expect(isValidSlug('my-team')).toBe(true)
    expect(isValidSlug('acme')).toBe(true)
    expect(isValidSlug('a1-b2')).toBe(true)
    expect(SLUG_REGEX.test('prod-01')).toBe(true)
  })

  it('rejects invalid slugs', () => {
    expect(isValidSlug('')).toBe(false)
    expect(isValidSlug('My-Team')).toBe(false)
    expect(isValidSlug('has spaces')).toBe(false)
    expect(isValidSlug('-leading')).toBe(false)
    expect(isValidSlug('trailing-')).toBe(false)
    expect(isValidSlug('under_score')).toBe(false)
  })

  it('slugifies display names', () => {
    expect(slugifyName('My Cool Team')).toBe('my-cool-team')
    expect(slugifyName('  ACME  ')).toBe('acme')
    expect(slugifyName('Hello!!!World')).toBe('hello-world')
    expect(slugifyName('---')).toBe('')
  })
})
