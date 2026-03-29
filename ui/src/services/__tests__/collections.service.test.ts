import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import {
  getCollections,
  getCollectionById,
  getCollectionByName,
  createCollection,
  updateCollection,
  deleteCollection,
  getCollectionRules,
  updateCollectionRules,
  exportCollections,
  importCollections,
} from '../collections.service'
import * as apiModule from '@/lib/api'
import type {
  Collection,
  CollectionListResponse,
  CollectionRule,
  CollectionImportResult,
  CollectionExportData,
} from '../collections.service'

const mockField = {
  name: 'title',
  type: 'text',
  required: true,
  unique: false,
}

const mockCollection: Collection = {
  id: 'col-1',
  name: 'posts',
  table_name: 'posts',
  schema: [mockField],
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const mockCollectionListResponse: CollectionListResponse = {
  items: [
    {
      id: 'col-1',
      name: 'posts',
      table_name: 'posts',
      fields_count: 1,
      records_count: 10,
      has_public_access: false,
      created_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'col-2',
      name: 'products',
      table_name: 'products',
      fields_count: 3,
      records_count: 5,
      has_public_access: true,
      created_at: '2024-02-01T00:00:00Z',
    },
  ],
  total: 2,
  page: 1,
  page_size: 25,
  total_pages: 1,
}

const mockCollectionRule: CollectionRule = {
  id: 'rule-1',
  collection_id: 'col-1',
  list_rule: null,
  view_rule: null,
  create_rule: '@is_authenticated',
  update_rule: '@owns_record()',
  delete_rule: '@owns_record()',
  list_fields: '*',
  view_fields: '*',
  create_fields: '*',
  update_fields: '*',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

// ─────────────────────────────────────────────────────────────────────────────
// getCollections()
// ─────────────────────────────────────────────────────────────────────────────

describe('Collections Service', () => {
  describe('getCollections()', () => {
    it('sends GET to /collections', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/collections', () => {
          requestReceived = true
          return HttpResponse.json(mockCollectionListResponse)
        })
      )

      await getCollections()
      expect(requestReceived).toBe(true)
    })

    it('returns collection list response on success', async () => {
      server.use(
        http.get('/api/v1/collections', () => HttpResponse.json(mockCollectionListResponse))
      )

      const result = await getCollections()
      expect(result).toEqual(mockCollectionListResponse)
    })

    it('passes query params to the request', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/collections', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockCollectionListResponse)
        })
      )

      await getCollections({ page: 2, page_size: 10, search: 'post' })

      expect(capturedUrl).toContain('page=2')
      expect(capturedUrl).toContain('page_size=10')
      expect(capturedUrl).toContain('search=post')
    })

    it('passes sort params to the request', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/collections', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockCollectionListResponse)
        })
      )

      await getCollections({ sort_by: 'name', sort_order: 'asc' })

      expect(capturedUrl).toContain('sort_by=name')
      expect(capturedUrl).toContain('sort_order=asc')
    })

    it('propagates API errors', async () => {
      server.use(
        http.get('/api/v1/collections', () =>
          HttpResponse.json({ detail: 'Forbidden' }, { status: 403 })
        )
      )

      await expect(getCollections()).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // getCollectionById()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('getCollectionById()', () => {
    it('sends GET to /collections/{id}', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/collections/col-1', () => {
          requestReceived = true
          return HttpResponse.json(mockCollection)
        })
      )

      await getCollectionById('col-1')
      expect(requestReceived).toBe(true)
    })

    it('returns collection detail on success', async () => {
      server.use(
        http.get('/api/v1/collections/col-1', () => HttpResponse.json(mockCollection))
      )

      const result = await getCollectionById('col-1')
      expect(result).toEqual(mockCollection)
    })

    it('returns schema in the response', async () => {
      server.use(
        http.get('/api/v1/collections/col-1', () => HttpResponse.json(mockCollection))
      )

      const result = await getCollectionById('col-1')
      expect(result.schema).toEqual([mockField])
    })

    it('propagates 404 when collection not found', async () => {
      server.use(
        http.get('/api/v1/collections/missing', () =>
          HttpResponse.json({ detail: 'Collection not found' }, { status: 404 })
        )
      )

      await expect(getCollectionById('missing')).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // getCollectionByName()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('getCollectionByName()', () => {
    it('searches collections and fetches full detail for exact name match', async () => {
      let detailFetched = false

      server.use(
        http.get('/api/v1/collections', () => HttpResponse.json(mockCollectionListResponse)),
        http.get('/api/v1/collections/col-1', () => {
          detailFetched = true
          return HttpResponse.json(mockCollection)
        })
      )

      await getCollectionByName('posts')
      expect(detailFetched).toBe(true)
    })

    it('throws when no exact name match found', async () => {
      server.use(
        http.get('/api/v1/collections', () =>
          HttpResponse.json({ ...mockCollectionListResponse, items: [] })
        )
      )

      await expect(getCollectionByName('nonexistent')).rejects.toThrow("Collection 'nonexistent' not found")
    })

    it('passes collection name as search param', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/collections', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockCollectionListResponse)
        }),
        http.get('/api/v1/collections/col-1', () => HttpResponse.json(mockCollection))
      )

      await getCollectionByName('posts')

      expect(capturedUrl).toContain('search=posts')
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // createCollection()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('createCollection()', () => {
    it('sends POST to /collections with schema payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/collections', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockCollection, { status: 201 })
        })
      )

      await createCollection({ name: 'posts', schema: [mockField] })

      expect(capturedBody).toEqual({ name: 'posts', schema: [mockField] })
    })

    it('returns created collection on success', async () => {
      server.use(
        http.post('/api/v1/collections', () =>
          HttpResponse.json(mockCollection, { status: 201 })
        )
      )

      const result = await createCollection({ name: 'posts', schema: [mockField] })
      expect(result).toEqual(mockCollection)
    })

    it('propagates API errors on duplicate name', async () => {
      server.use(
        http.post('/api/v1/collections', () =>
          HttpResponse.json({ detail: 'Collection already exists' }, { status: 409 })
        )
      )

      await expect(createCollection({ name: 'posts', schema: [] })).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // updateCollection()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('updateCollection()', () => {
    it('sends PUT to /collections/{id} with schema payload', async () => {
      let capturedBody: Record<string, unknown> | null = null
      const updatedSchema = [mockField, { name: 'body', type: 'text' }]

      server.use(
        http.put('/api/v1/collections/col-1', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json({ ...mockCollection, schema: updatedSchema })
        })
      )

      await updateCollection('col-1', { schema: updatedSchema })

      expect(capturedBody).toEqual({ schema: updatedSchema })
    })

    it('returns updated collection on success', async () => {
      const updatedSchema = [mockField, { name: 'body', type: 'text' }]
      const updatedCollection = { ...mockCollection, schema: updatedSchema }

      server.use(
        http.put('/api/v1/collections/col-1', () => HttpResponse.json(updatedCollection))
      )

      const result = await updateCollection('col-1', { schema: updatedSchema })
      expect(result.schema).toHaveLength(2)
    })

    it('propagates 404 when collection not found', async () => {
      server.use(
        http.put('/api/v1/collections/missing', () =>
          HttpResponse.json({ detail: 'Collection not found' }, { status: 404 })
        )
      )

      await expect(updateCollection('missing', { schema: [] })).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // deleteCollection()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('deleteCollection()', () => {
    it('sends DELETE to /collections/{id}', async () => {
      let requestReceived = false

      server.use(
        http.delete('/api/v1/collections/col-1', () => {
          requestReceived = true
          return new HttpResponse(null, { status: 204 })
        })
      )

      await deleteCollection('col-1')
      expect(requestReceived).toBe(true)
    })

    it('resolves without a return value on success', async () => {
      server.use(
        http.delete('/api/v1/collections/col-1', () =>
          new HttpResponse(null, { status: 204 })
        )
      )

      const result = await deleteCollection('col-1')
      expect(result).toBeUndefined()
    })

    it('propagates 404 when collection not found', async () => {
      server.use(
        http.delete('/api/v1/collections/missing', () =>
          HttpResponse.json({ detail: 'Collection not found' }, { status: 404 })
        )
      )

      await expect(deleteCollection('missing')).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // getCollectionRules()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('getCollectionRules()', () => {
    it('sends GET to /collections/{name}/rules', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/collections/posts/rules', () => {
          requestReceived = true
          return HttpResponse.json(mockCollectionRule)
        })
      )

      await getCollectionRules('posts')
      expect(requestReceived).toBe(true)
    })

    it('returns collection rules on success', async () => {
      server.use(
        http.get('/api/v1/collections/posts/rules', () => HttpResponse.json(mockCollectionRule))
      )

      const result = await getCollectionRules('posts')
      expect(result).toEqual(mockCollectionRule)
    })

    it('returns null rule values when rules are open', async () => {
      const openRules = { ...mockCollectionRule, list_rule: null, view_rule: null }

      server.use(
        http.get('/api/v1/collections/posts/rules', () => HttpResponse.json(openRules))
      )

      const result = await getCollectionRules('posts')
      expect(result.list_rule).toBeNull()
      expect(result.view_rule).toBeNull()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // updateCollectionRules()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('updateCollectionRules()', () => {
    it('sends PUT to /collections/{name}/rules with payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.put('/api/v1/collections/posts/rules', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockCollectionRule)
        })
      )

      await updateCollectionRules('posts', { create_rule: '@is_authenticated' })

      expect(capturedBody).toEqual({ create_rule: '@is_authenticated' })
    })

    it('returns updated rules on success', async () => {
      server.use(
        http.put('/api/v1/collections/posts/rules', () => HttpResponse.json(mockCollectionRule))
      )

      const result = await updateCollectionRules('posts', { create_rule: '@is_authenticated' })
      expect(result).toEqual(mockCollectionRule)
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // importCollections()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('importCollections()', () => {
    const mockExportData: CollectionExportData = {
      version: '1.0',
      exported_at: '2024-01-01T00:00:00Z',
      exported_by: 'superadmin',
      collections: [
        {
          name: 'posts',
          schema: [mockField],
          rules: {
            list_rule: null,
            view_rule: null,
            create_rule: null,
            update_rule: null,
            delete_rule: null,
            list_fields: '*',
            view_fields: '*',
            create_fields: '*',
            update_fields: '*',
          },
        },
      ],
    }

    const mockImportResult: CollectionImportResult = {
      success: true,
      imported_count: 1,
      skipped_count: 0,
      updated_count: 0,
      failed_count: 0,
      collections: [{ name: 'posts', status: 'imported', message: 'Imported successfully' }],
      migrations_created: ['rev_001'],
    }

    it('sends POST to /collections/import with data and strategy', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/collections/import', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockImportResult)
        })
      )

      await importCollections(mockExportData, 'skip')

      expect(capturedBody).toMatchObject({ strategy: 'skip', generate_migrations: true })
    })

    it('defaults strategy to "error"', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/collections/import', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockImportResult)
        })
      )

      await importCollections(mockExportData)

      expect(capturedBody).toMatchObject({ strategy: 'error' })
    })

    it('always sets generate_migrations to true', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/collections/import', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockImportResult)
        })
      )

      await importCollections(mockExportData)

      expect(capturedBody?.generate_migrations).toBe(true)
    })

    it('returns import result on success', async () => {
      server.use(
        http.post('/api/v1/collections/import', () => HttpResponse.json(mockImportResult))
      )

      const result = await importCollections(mockExportData)
      expect(result).toEqual(mockImportResult)
    })

    it('propagates API errors', async () => {
      server.use(
        http.post('/api/v1/collections/import', () =>
          HttpResponse.json({ detail: 'Conflict' }, { status: 409 })
        )
      )

      await expect(importCollections(mockExportData)).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // exportCollections()
  //
  // exportCollections() uses responseType: 'blob' and triggers DOM download
  // APIs. MSW + XHR + blob is unsupported in the jsdom environment, so we mock
  // apiClient.get directly and verify the URL/params contract instead.
  // ─────────────────────────────────────────────────────────────────────────────

  describe('exportCollections()', () => {
    let apiGetSpy: ReturnType<typeof vi.spyOn>

    beforeEach(() => {
      const fakeResponse = {
        data: new Blob(['{}'], { type: 'application/json' }),
        headers: {},
      }
      apiGetSpy = vi.spyOn(apiModule.apiClient, 'get').mockResolvedValue(fakeResponse)

      vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:http://localhost/mock-url')
      vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined)

      const mockLink = { href: '', download: '', click: vi.fn() }
      vi.spyOn(document, 'createElement').mockReturnValue(mockLink as unknown as HTMLElement)
      vi.spyOn(document.body, 'appendChild').mockImplementation(() => mockLink as unknown as Node)
      vi.spyOn(document.body, 'removeChild').mockImplementation(() => mockLink as unknown as Node)
    })

    afterEach(() => {
      vi.restoreAllMocks()
    })

    it('calls GET /collections/export', async () => {
      await exportCollections()

      expect(apiGetSpy).toHaveBeenCalledWith(
        '/collections/export',
        expect.objectContaining({ responseType: 'blob' })
      )
    })

    it('passes collection_ids as comma-separated param when provided', async () => {
      await exportCollections(['col-1', 'col-2'])

      expect(apiGetSpy).toHaveBeenCalledWith(
        '/collections/export',
        expect.objectContaining({
          params: { collection_ids: 'col-1,col-2' },
        })
      )
    })

    it('sends empty params when no collection_ids provided', async () => {
      await exportCollections()

      expect(apiGetSpy).toHaveBeenCalledWith(
        '/collections/export',
        expect.objectContaining({ params: {} })
      )
    })

    it('sends empty params when empty array provided', async () => {
      await exportCollections([])

      expect(apiGetSpy).toHaveBeenCalledWith(
        '/collections/export',
        expect.objectContaining({ params: {} })
      )
    })
  })
})
