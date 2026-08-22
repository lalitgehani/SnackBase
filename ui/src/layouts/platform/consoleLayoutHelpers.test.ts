import { describe, it, expect } from 'vitest'
import { getConsolePageTitle } from './consoleLayoutHelpers'

describe('getConsolePageTitle', () => {
  it('returns Organizations for org list', () => {
    expect(getConsolePageTitle('/organizations')).toBe('Organizations')
  })

  it('returns Projects for project paths', () => {
    expect(getConsolePageTitle('/organizations/abc/projects')).toBe('Projects')
  })

  it('returns Environments for environment paths', () => {
    expect(
      getConsolePageTitle('/organizations/abc/projects/p1/environments'),
    ).toBe('Environments')
  })

  it('returns Account for account settings', () => {
    expect(getConsolePageTitle('/account')).toBe('Account')
  })

  it('returns Create organization / Create project titles', () => {
    expect(getConsolePageTitle('/organizations/new')).toBe('Create organization')
    expect(getConsolePageTitle('/organizations/abc/projects/new')).toBe(
      'Create project',
    )
  })
})
