import { describe, it, expect } from 'vitest'
import {
  isNavActive,
  isOrganizationsNavActive,
  isProjectsNavActive,
} from './consoleSidebarNav'

describe('isNavActive', () => {
  it('matches exact path', () => {
    expect(isNavActive('/account', '/account')).toBe(true)
  })

  it('matches nested paths under the url', () => {
    expect(isNavActive('/account/security', '/account')).toBe(true)
  })

  it('does not match unrelated paths', () => {
    expect(isNavActive('/organizations', '/account')).toBe(false)
  })
})

describe('isOrganizationsNavActive', () => {
  it('is active on org list and create', () => {
    expect(isOrganizationsNavActive('/organizations')).toBe(true)
    expect(isOrganizationsNavActive('/organizations/new')).toBe(true)
  })

  it('is not active on projects or environments', () => {
    expect(isOrganizationsNavActive('/organizations/abc/projects')).toBe(false)
    expect(isOrganizationsNavActive('/organizations/abc/projects/new')).toBe(
      false,
    )
    expect(
      isOrganizationsNavActive('/organizations/abc/projects/p1/environments'),
    ).toBe(false)
  })

  it('is not active on other sections', () => {
    expect(isOrganizationsNavActive('/account')).toBe(false)
  })
})

describe('isProjectsNavActive', () => {
  it('is active on project and environment paths', () => {
    expect(isProjectsNavActive('/organizations/abc/projects')).toBe(true)
    expect(isProjectsNavActive('/organizations/abc/projects/new')).toBe(true)
    expect(
      isProjectsNavActive('/organizations/abc/projects/p1/environments'),
    ).toBe(true)
  })

  it('is not active on org list', () => {
    expect(isProjectsNavActive('/organizations')).toBe(false)
    expect(isProjectsNavActive('/organizations/new')).toBe(false)
  })
})
