import { describe, it, expect } from 'vitest'
import {
  SYSTEM_ACCOUNT_ID,
  SYSTEM_ACCOUNT_CODE,
  SYSTEM_ACCOUNT_SLUG,
  isSuperadminAccount,
} from '@/lib/auth'

describe('isSuperadminAccount', () => {
  it('returns true for system account nil UUID', () => {
    expect(isSuperadminAccount({ id: SYSTEM_ACCOUNT_ID, slug: 'system' })).toBe(true)
  })

  it('returns true for system account code as id (legacy/compat)', () => {
    expect(isSuperadminAccount({ id: SYSTEM_ACCOUNT_CODE })).toBe(true)
  })

  it('returns true for system account slug', () => {
    expect(isSuperadminAccount({ id: 'other', slug: SYSTEM_ACCOUNT_SLUG })).toBe(true)
  })

  it('returns false for tenant accounts', () => {
    expect(
      isSuperadminAccount({
        id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        slug: 'acme',
      }),
    ).toBe(false)
  })

  it('returns false for null/undefined', () => {
    expect(isSuperadminAccount(null)).toBe(false)
    expect(isSuperadminAccount(undefined)).toBe(false)
  })
})
