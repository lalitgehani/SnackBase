import type { SnackBaseClient } from '@snackbase/sdk'
import type { Region } from '@/types/control-plane'

/**
 * List regions available for project create from the system `regions` codelist.
 * Effective values are the sole catalog SoT (no collection fan-out).
 */
export async function listAvailableRegions(client: SnackBaseClient): Promise<Region[]> {
  // Prefer SDK codelists API when present; fall back to raw HTTP path on client.
  const codelists = (client as SnackBaseClient & {
    codelists?: {
      getValues: (
        code: string,
        opts?: { lang?: string; active?: boolean },
      ) => Promise<
        Array<{
          code: string
          label: string
          metadata?: Record<string, unknown> | null
          sort_order?: number
        }>
      >
    }
  }).codelists

  let values: Array<{
    code: string
    label: string
    metadata?: Record<string, unknown> | null
    sort_order?: number
  }>

  if (codelists?.getValues) {
    values = await codelists.getValues('regions', { lang: 'en', active: true })
  } else {
    // Raw path used until SDK is upgraded in the console package
    const http = (
      client as unknown as {
        httpClient?: { get: (url: string) => Promise<{ data: unknown }> }
      }
    ).httpClient
    if (!http?.get) {
      throw new Error('Codelist API unavailable on SnackBase client')
    }
    const res = await http.get('/api/v1/codelists/regions/values?lang=en&active=true')
    const data = res.data
    values = Array.isArray(data) ? data : []
  }

  return values.map((v) => {
    const meta = (v.metadata || {}) as Record<string, unknown>
    const status =
      (typeof meta.status === 'string' ? meta.status : 'available') as Region['status']
    return {
      id: v.code,
      code: v.code,
      name: v.label,
      country: typeof meta.country === 'string' ? meta.country : '',
      status,
      sort_order: v.sort_order ?? 0,
    } satisfies Region
  })
}

export function isRegionAvailable(regions: Region[], code: string): boolean {
  return regions.some(
    (r) => r.code === code && (r.status === 'available' || !r.status),
  )
}
