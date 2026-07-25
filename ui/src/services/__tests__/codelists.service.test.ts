import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import {
  listCodelists,
  getEffectiveValues,
  createCodelist,
  setOverride,
  isValidCodelistCode,
} from '../codelists.service'
import type { Codelist, EffectiveCodelistValue } from '@/types/codelist'

const mockList: Codelist[] = [
  {
    id: '1',
    code: 'regions',
    name: 'Cloud Regions',
    scope: 'system',
    account_id: '00000000-0000-0000-0000-000000000000',
    is_system: true,
    is_extensible: false,
    is_active: true,
    is_builtin: true,
  },
]

const mockValues: EffectiveCodelistValue[] = [
  {
    code: 'eu-01',
    label: 'EU Central (Germany)',
    is_default: false,
    sort_order: 1,
    scope: 'system',
    is_active: true,
  },
]

describe('Codelists Service', () => {
  describe('listCodelists()', () => {
    it('sends GET to /codelists and returns data', async () => {
      server.use(
        http.get('/api/v1/codelists', () => HttpResponse.json(mockList)),
      )
      const result = await listCodelists()
      expect(result).toEqual(mockList)
      expect(result[0].code).toBe('regions')
    })
  })

  describe('getEffectiveValues()', () => {
    it('requests values with lang query', async () => {
      let captured = ''
      server.use(
        http.get('/api/v1/codelists/regions/values', ({ request }) => {
          captured = request.url
          return HttpResponse.json(mockValues)
        }),
      )
      const result = await getEffectiveValues('regions', { lang: 'en' })
      expect(result).toEqual(mockValues)
      expect(captured).toContain('lang=en')
      expect(result[0].code).toBe('eu-01')
    })
  })

  describe('createCodelist()', () => {
    it('POSTs create body', async () => {
      server.use(
        http.post('/api/v1/codelists', async ({ request }) => {
          const body = (await request.json()) as { code: string }
          return HttpResponse.json({
            ...mockList[0],
            code: body.code,
            is_builtin: false,
          })
        }),
      )
      const created = await createCodelist({
        code: 'statuses',
        name: 'Statuses',
        scope: 'account',
      })
      expect(created.code).toBe('statuses')
    })
  })

  describe('setOverride()', () => {
    it('PUTs override payload', async () => {
      server.use(
        http.put('/api/v1/codelists/regions/values/eu-01/override', async ({ request }) => {
          const body = (await request.json()) as { visibility: string }
          return HttpResponse.json({
            id: 'ov1',
            account_id: 'a',
            codelist_id: '1',
            value_id: 'v1',
            visibility: body.visibility,
            is_default: false,
          })
        }),
      )
      const ov = await setOverride('regions', 'eu-01', { visibility: 'hidden' })
      expect(ov.visibility).toBe('hidden')
    })
  })

  describe('isValidCodelistCode()', () => {
    it('accepts valid codes and rejects invalid', () => {
      expect(isValidCodelistCode('regions')).toBe(true)
      expect(isValidCodelistCode('my_list2')).toBe(true)
      expect(isValidCodelistCode('Bad-Code')).toBe(false)
      expect(isValidCodelistCode('1abc')).toBe(false)
    })
  })
})
