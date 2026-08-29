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

  it('drops provider metadata so the Console never sees infrastructure', async () => {
    const getValues = vi.fn(async () => [
      {
        code: 'eu-02',
        label: 'EU West (Amsterdam)',
        metadata: {
          country: 'NL',
          status: 'available',
          provider: 'railway',
          provider_region: 'europe-west4-drams3a',
          domain_suffix: 'instance.snackbase.dev',
          scheme: 'https',
        },
        sort_order: 2,
      },
    ])
    const client = { codelists: { getValues } } as unknown as SnackBaseClient
    const [region] = await listAvailableRegions(client)

    expect(Object.keys(region).sort()).toEqual([
      'code',
      'country',
      'id',
      'name',
      'sort_order',
      'status',
    ])
    for (const leaked of ['provider', 'provider_region', 'domain_suffix', 'scheme']) {
      expect(region).not.toHaveProperty(leaked)
    }
    expect(JSON.stringify(region)).not.toContain('railway')
  })

  it('returns regions in sort_order', async () => {
    const getValues = vi.fn(async () => [
      {
        code: 'eu-02',
        label: 'EU West (Amsterdam)',
        metadata: { country: 'NL', status: 'available' },
        sort_order: 2,
      },
      {
        code: 'eu-01',
        label: 'EU Central (Germany)',
        metadata: { country: 'DE', status: 'available' },
        sort_order: 1,
      },
    ])
    const client = { codelists: { getValues } } as unknown as SnackBaseClient
    const regions = await listAvailableRegions(client)
    expect(regions.map((r) => r.code)).toEqual(['eu-01', 'eu-02'])
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
