import { describe, it, expect, vi } from 'vitest'
import { isRegionAvailable, listAvailableRegions } from './regions'
import type { SnackBaseClient } from '@snackbase/sdk'

describe('listAvailableRegions (codelist)', () => {
  it('maps effective codelist values to Region rows', async () => {
    const getValues = vi.fn(async () => [
      {
        code: 'eu-01',
        label: 'EU Central (Germany)',
        metadata: { country: 'DE', status: 'available' },
        sort_order: 1,
      },
    ])
    const client = { codelists: { getValues } } as unknown as SnackBaseClient
    const regions = await listAvailableRegions(client)
    expect(getValues).toHaveBeenCalledWith('regions', { lang: 'en', active: true })
    expect(regions).toHaveLength(1)
    expect(regions[0].code).toBe('eu-01')
    expect(regions[0].name).toBe('EU Central (Germany)')
    expect(regions[0].status).toBe('available')
  })

  it('isRegionAvailable checks code + status', () => {
    const regions = [
      {
        id: 'eu-01',
        code: 'eu-01',
        name: 'EU',
        country: 'DE',
        status: 'available' as const,
        sort_order: 1,
      },
      {
        id: 'x',
        code: 'x',
        name: 'X',
        country: 'XX',
        status: 'unavailable' as const,
        sort_order: 2,
      },
    ]
    expect(isRegionAvailable(regions, 'eu-01')).toBe(true)
    expect(isRegionAvailable(regions, 'x')).toBe(false)
    expect(isRegionAvailable(regions, 'nope')).toBe(false)
  })
})
