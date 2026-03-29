import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import {
  getRecords,
  getRecordById,
  createRecord,
  updateRecord,
  patchRecord,
  deleteRecord,
  batchCreateRecords,
  batchUpdateRecords,
  batchDeleteRecords,
  aggregateRecords,
} from '../records.service'
import type { RecordDetail, RecordData } from '../records.service'

const mockRecord: RecordDetail = {
  id: 'rec-1',
  account_id: 'AB1234',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  created_by: 'user-1',
  updated_by: 'user-1',
  title: 'Hello World',
  body: 'Some content',
}

const mockRecordListResponse = {
  items: [mockRecord],
  total: 1,
  skip: 0,
  limit: 25,
}

// ─────────────────────────────────────────────────────────────────────────────
// getRecords()
// ─────────────────────────────────────────────────────────────────────────────

describe('Records Service', () => {
  describe('getRecords()', () => {
    it('sends GET to /records/{collection}', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/records/posts', () => {
          requestReceived = true
          return HttpResponse.json(mockRecordListResponse)
        })
      )

      await getRecords({ collection: 'posts' })
      expect(requestReceived).toBe(true)
    })

    it('returns list response on success', async () => {
      server.use(
        http.get('/api/v1/records/posts', () => HttpResponse.json(mockRecordListResponse))
      )

      const result = await getRecords({ collection: 'posts' })
      expect(result).toEqual(mockRecordListResponse)
    })

    it('passes pagination params (skip, limit)', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/records/posts', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockRecordListResponse)
        })
      )

      await getRecords({ collection: 'posts', skip: 10, limit: 5 })

      expect(capturedUrl).toContain('skip=10')
      expect(capturedUrl).toContain('limit=5')
    })

    it('passes cursor pagination params', async () => {
      let capturedUrl: string | null = null
      const cursorResponse = {
        items: [mockRecord],
        next_cursor: 'cursor-abc',
        prev_cursor: null,
        has_more: true,
      }

      server.use(
        http.get('/api/v1/records/posts', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(cursorResponse)
        })
      )

      await getRecords({ collection: 'posts', cursor: 'cursor-abc', include_count: true })

      expect(capturedUrl).toContain('cursor=cursor-abc')
      expect(capturedUrl).toContain('include_count=true')
    })

    it('passes sort and filter params', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/records/posts', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockRecordListResponse)
        })
      )

      await getRecords({ collection: 'posts', sort: '-created_at', filter: 'status="published"' })

      expect(capturedUrl).toContain('sort=-created_at')
      expect(capturedUrl).toContain('filter=')
    })

    it('does not include collection in query params', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/records/posts', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockRecordListResponse)
        })
      )

      await getRecords({ collection: 'posts' })

      expect(capturedUrl).not.toContain('collection=posts')
    })

    it('propagates API errors', async () => {
      server.use(
        http.get('/api/v1/records/posts', () =>
          HttpResponse.json({ detail: 'Forbidden' }, { status: 403 })
        )
      )

      await expect(getRecords({ collection: 'posts' })).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // getRecordById()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('getRecordById()', () => {
    it('sends GET to /records/{collection}/{id}', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/records/posts/rec-1', () => {
          requestReceived = true
          return HttpResponse.json(mockRecord)
        })
      )

      await getRecordById('posts', 'rec-1')
      expect(requestReceived).toBe(true)
    })

    it('returns record detail on success', async () => {
      server.use(
        http.get('/api/v1/records/posts/rec-1', () => HttpResponse.json(mockRecord))
      )

      const result = await getRecordById('posts', 'rec-1')
      expect(result).toEqual(mockRecord)
    })

    it('propagates 404 when record not found', async () => {
      server.use(
        http.get('/api/v1/records/posts/missing', () =>
          HttpResponse.json({ detail: 'Record not found' }, { status: 404 })
        )
      )

      await expect(getRecordById('posts', 'missing')).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // createRecord()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('createRecord()', () => {
    it('sends POST to /records/{collection} with payload', async () => {
      let capturedBody: RecordData | null = null
      const newRecord: RecordData = { title: 'New Post', body: 'Content here' }

      server.use(
        http.post('/api/v1/records/posts', async ({ request }) => {
          capturedBody = (await request.json()) as RecordData
          return HttpResponse.json(mockRecord, { status: 201 })
        })
      )

      await createRecord('posts', newRecord)

      expect(capturedBody).toEqual(newRecord)
    })

    it('returns created record on success', async () => {
      server.use(
        http.post('/api/v1/records/posts', () =>
          HttpResponse.json(mockRecord, { status: 201 })
        )
      )

      const result = await createRecord('posts', { title: 'New Post' })
      expect(result).toEqual(mockRecord)
    })

    it('propagates validation errors', async () => {
      server.use(
        http.post('/api/v1/records/posts', () =>
          HttpResponse.json({ detail: 'Validation error' }, { status: 422 })
        )
      )

      await expect(createRecord('posts', {})).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // updateRecord() — full PUT replacement
  // ─────────────────────────────────────────────────────────────────────────────

  describe('updateRecord()', () => {
    it('sends PUT to /records/{collection}/{id} with payload', async () => {
      let capturedBody: RecordData | null = null
      const updateData: RecordData = { title: 'Updated', body: 'New content' }

      server.use(
        http.put('/api/v1/records/posts/rec-1', async ({ request }) => {
          capturedBody = (await request.json()) as RecordData
          return HttpResponse.json({ ...mockRecord, ...updateData })
        })
      )

      await updateRecord('posts', 'rec-1', updateData)

      expect(capturedBody).toEqual(updateData)
    })

    it('returns updated record on success', async () => {
      const updateData: RecordData = { title: 'Updated' }

      server.use(
        http.put('/api/v1/records/posts/rec-1', () =>
          HttpResponse.json({ ...mockRecord, ...updateData })
        )
      )

      const result = await updateRecord('posts', 'rec-1', updateData)
      expect(result.title).toBe('Updated')
    })

    it('propagates 404 when record not found', async () => {
      server.use(
        http.put('/api/v1/records/posts/missing', () =>
          HttpResponse.json({ detail: 'Record not found' }, { status: 404 })
        )
      )

      await expect(updateRecord('posts', 'missing', { title: 'x' })).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // patchRecord() — partial PATCH update
  // ─────────────────────────────────────────────────────────────────────────────

  describe('patchRecord()', () => {
    it('sends PATCH to /records/{collection}/{id} with partial payload', async () => {
      let capturedBody: Partial<RecordData> | null = null
      const patchData: Partial<RecordData> = { title: 'Patched title' }

      server.use(
        http.patch('/api/v1/records/posts/rec-1', async ({ request }) => {
          capturedBody = (await request.json()) as Partial<RecordData>
          return HttpResponse.json({ ...mockRecord, ...patchData })
        })
      )

      await patchRecord('posts', 'rec-1', patchData)

      expect(capturedBody).toEqual(patchData)
    })

    it('returns patched record on success', async () => {
      server.use(
        http.patch('/api/v1/records/posts/rec-1', () =>
          HttpResponse.json({ ...mockRecord, title: 'Patched' })
        )
      )

      const result = await patchRecord('posts', 'rec-1', { title: 'Patched' })
      expect(result.title).toBe('Patched')
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // deleteRecord()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('deleteRecord()', () => {
    it('sends DELETE to /records/{collection}/{id}', async () => {
      let requestReceived = false

      server.use(
        http.delete('/api/v1/records/posts/rec-1', () => {
          requestReceived = true
          return new HttpResponse(null, { status: 204 })
        })
      )

      await deleteRecord('posts', 'rec-1')
      expect(requestReceived).toBe(true)
    })

    it('resolves without a return value on success', async () => {
      server.use(
        http.delete('/api/v1/records/posts/rec-1', () =>
          new HttpResponse(null, { status: 204 })
        )
      )

      const result = await deleteRecord('posts', 'rec-1')
      expect(result).toBeUndefined()
    })

    it('propagates 404 when record not found', async () => {
      server.use(
        http.delete('/api/v1/records/posts/missing', () =>
          HttpResponse.json({ detail: 'Record not found' }, { status: 404 })
        )
      )

      await expect(deleteRecord('posts', 'missing')).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // batchCreateRecords()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('batchCreateRecords()', () => {
    const mockBatchCreateResponse = {
      created: [mockRecord, { ...mockRecord, id: 'rec-2', title: 'Second Post' }],
      count: 2,
    }

    it('sends POST to /records/{collection}/batch with records array', async () => {
      let capturedBody: Record<string, unknown> | null = null
      const records = [{ title: 'Post 1' }, { title: 'Post 2' }]

      server.use(
        http.post('/api/v1/records/posts/batch', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockBatchCreateResponse, { status: 201 })
        })
      )

      await batchCreateRecords('posts', records)

      expect(capturedBody).toEqual({ records })
    })

    it('returns batch create response on success', async () => {
      server.use(
        http.post('/api/v1/records/posts/batch', () =>
          HttpResponse.json(mockBatchCreateResponse, { status: 201 })
        )
      )

      const result = await batchCreateRecords('posts', [{ title: 'Post 1' }])
      expect(result.count).toBe(2)
      expect(result.created).toHaveLength(2)
    })

    it('propagates errors when batch fails', async () => {
      server.use(
        http.post('/api/v1/records/posts/batch', () =>
          HttpResponse.json({ detail: 'Validation failed' }, { status: 422 })
        )
      )

      await expect(batchCreateRecords('posts', [{}])).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // batchUpdateRecords()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('batchUpdateRecords()', () => {
    const mockBatchUpdateResponse = {
      updated: [mockRecord],
      count: 1,
    }

    it('sends PATCH to /records/{collection}/batch with updates array', async () => {
      let capturedBody: Record<string, unknown> | null = null
      const updates = [{ id: 'rec-1', data: { title: 'Updated' } }]

      server.use(
        http.patch('/api/v1/records/posts/batch', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockBatchUpdateResponse)
        })
      )

      await batchUpdateRecords('posts', updates)

      expect(capturedBody).toEqual({ records: updates })
    })

    it('returns batch update response on success', async () => {
      server.use(
        http.patch('/api/v1/records/posts/batch', () =>
          HttpResponse.json(mockBatchUpdateResponse)
        )
      )

      const result = await batchUpdateRecords('posts', [{ id: 'rec-1', data: { title: 'x' } }])
      expect(result.count).toBe(1)
      expect(result.updated).toHaveLength(1)
    })

    it('propagates 404 when any record id does not exist', async () => {
      server.use(
        http.patch('/api/v1/records/posts/batch', () =>
          HttpResponse.json({ detail: 'Record not found' }, { status: 404 })
        )
      )

      await expect(
        batchUpdateRecords('posts', [{ id: 'missing', data: {} }])
      ).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // batchDeleteRecords()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('batchDeleteRecords()', () => {
    const mockBatchDeleteResponse = {
      deleted: ['rec-1', 'rec-2'],
      count: 2,
    }

    it('sends DELETE to /records/{collection}/batch with ids in request body', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.delete('/api/v1/records/posts/batch', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockBatchDeleteResponse)
        })
      )

      await batchDeleteRecords('posts', ['rec-1', 'rec-2'])

      expect(capturedBody).toEqual({ ids: ['rec-1', 'rec-2'] })
    })

    it('returns batch delete response on success', async () => {
      server.use(
        http.delete('/api/v1/records/posts/batch', () =>
          HttpResponse.json(mockBatchDeleteResponse)
        )
      )

      const result = await batchDeleteRecords('posts', ['rec-1', 'rec-2'])
      expect(result.count).toBe(2)
      expect(result.deleted).toEqual(['rec-1', 'rec-2'])
    })

    it('propagates 404 when any id does not exist', async () => {
      server.use(
        http.delete('/api/v1/records/posts/batch', () =>
          HttpResponse.json({ detail: 'Record not found' }, { status: 404 })
        )
      )

      await expect(batchDeleteRecords('posts', ['missing'])).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // aggregateRecords()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('aggregateRecords()', () => {
    const mockAggregationResponse = {
      results: [{ status: 'published', count: 42 }],
      total_groups: 1,
    }

    it('sends GET to /records/{collection}/aggregate', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/records/posts/aggregate', () => {
          requestReceived = true
          return HttpResponse.json(mockAggregationResponse)
        })
      )

      await aggregateRecords('posts', { functions: 'count()' })
      expect(requestReceived).toBe(true)
    })

    it('passes aggregation params to the request', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/records/posts/aggregate', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockAggregationResponse)
        })
      )

      await aggregateRecords('posts', {
        functions: 'count(),sum(price)',
        group_by: 'status',
        filter: 'status="published"',
      })

      expect(capturedUrl).toContain('functions=')
      expect(capturedUrl).toContain('group_by=status')
    })

    it('returns aggregation response on success', async () => {
      server.use(
        http.get('/api/v1/records/posts/aggregate', () =>
          HttpResponse.json(mockAggregationResponse)
        )
      )

      const result = await aggregateRecords('posts', { functions: 'count()' })
      expect(result).toEqual(mockAggregationResponse)
    })

    it('propagates API errors', async () => {
      server.use(
        http.get('/api/v1/records/posts/aggregate', () =>
          HttpResponse.json({ detail: 'Invalid aggregation' }, { status: 400 })
        )
      )

      await expect(aggregateRecords('posts', { functions: 'invalid()' })).rejects.toThrow()
    })
  })
})
