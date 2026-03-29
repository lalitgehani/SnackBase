import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { getAuditLogs, getAuditLog, exportAuditLogs } from '../audit.service'
import * as apiModule from '@/lib/api'
import type { AuditLogItem, AuditLogListResponse } from '../audit.service'

const mockAuditLogItem: AuditLogItem = {
  id: 1,
  account_id: 'AB1234',
  operation: 'CREATE',
  table_name: 'posts',
  record_id: 'rec-1',
  column_name: 'title',
  old_value: null,
  new_value: 'Hello World',
  user_id: 'user-1',
  user_email: 'admin@example.com',
  user_name: 'Admin User',
  es_username: null,
  es_reason: null,
  es_timestamp: null,
  ip_address: '127.0.0.1',
  user_agent: 'Mozilla/5.0',
  request_id: 'req-abc',
  occurred_at: '2024-01-01T00:00:00Z',
  checksum: null,
  previous_hash: null,
  extra_metadata: null,
}

const mockAuditLogListResponse: AuditLogListResponse = {
  items: [mockAuditLogItem],
  total: 1,
  skip: 0,
  limit: 50,
}

// ─────────────────────────────────────────────────────────────────────────────
// getAuditLogs()
// ─────────────────────────────────────────────────────────────────────────────

describe('Audit Service', () => {
  describe('getAuditLogs()', () => {
    it('sends GET to /audit-logs/', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/audit-logs/', () => {
          requestReceived = true
          return HttpResponse.json(mockAuditLogListResponse)
        })
      )

      await getAuditLogs({})
      expect(requestReceived).toBe(true)
    })

    it('returns audit log list on success', async () => {
      server.use(
        http.get('/api/v1/audit-logs/', () => HttpResponse.json(mockAuditLogListResponse))
      )

      const result = await getAuditLogs({})
      expect(result).toEqual(mockAuditLogListResponse)
    })

    it('passes filter params to the request', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/audit-logs/', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockAuditLogListResponse)
        })
      )

      await getAuditLogs({ account_id: 'AB1234', table_name: 'posts', operation: 'CREATE' })

      expect(capturedUrl).toContain('account_id=AB1234')
      expect(capturedUrl).toContain('table_name=posts')
      expect(capturedUrl).toContain('operation=CREATE')
    })

    it('passes pagination params to the request', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/audit-logs/', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockAuditLogListResponse)
        })
      )

      await getAuditLogs({ skip: 10, limit: 25 })

      expect(capturedUrl).toContain('skip=10')
      expect(capturedUrl).toContain('limit=25')
    })

    it('passes date range params to the request', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/audit-logs/', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockAuditLogListResponse)
        })
      )

      await getAuditLogs({ from_date: '2024-01-01', to_date: '2024-12-31' })

      expect(capturedUrl).toContain('from_date=2024-01-01')
      expect(capturedUrl).toContain('to_date=2024-12-31')
    })

    it('passes sort params to the request', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/audit-logs/', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockAuditLogListResponse)
        })
      )

      await getAuditLogs({ sort_by: 'occurred_at', sort_order: 'desc' })

      expect(capturedUrl).toContain('sort_by=occurred_at')
      expect(capturedUrl).toContain('sort_order=desc')
    })

    it('propagates API errors', async () => {
      server.use(
        http.get('/api/v1/audit-logs/', () =>
          HttpResponse.json({ detail: 'Forbidden' }, { status: 403 })
        )
      )

      await expect(getAuditLogs({})).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // getAuditLog()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('getAuditLog()', () => {
    it('sends GET to /audit-logs/{id}', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/audit-logs/1', () => {
          requestReceived = true
          return HttpResponse.json(mockAuditLogItem)
        })
      )

      await getAuditLog(1)
      expect(requestReceived).toBe(true)
    })

    it('returns a single audit log on success', async () => {
      server.use(
        http.get('/api/v1/audit-logs/1', () => HttpResponse.json(mockAuditLogItem))
      )

      const result = await getAuditLog(1)
      expect(result).toEqual(mockAuditLogItem)
    })

    it('returns correct operation and table_name fields', async () => {
      server.use(
        http.get('/api/v1/audit-logs/1', () => HttpResponse.json(mockAuditLogItem))
      )

      const result = await getAuditLog(1)
      expect(result.operation).toBe('CREATE')
      expect(result.table_name).toBe('posts')
    })

    it('propagates 404 when audit log not found', async () => {
      server.use(
        http.get('/api/v1/audit-logs/999', () =>
          HttpResponse.json({ detail: 'Audit log not found' }, { status: 404 })
        )
      )

      await expect(getAuditLog(999)).rejects.toThrow()
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // exportAuditLogs()
  //
  // exportAuditLogs() uses responseType: 'blob' and triggers DOM download APIs.
  // MSW + XHR + blob is unsupported in the jsdom environment, so we mock
  // apiClient.get directly and verify the URL/params contract instead.
  // ─────────────────────────────────────────────────────────────────────────────

  describe('exportAuditLogs()', () => {
    let apiGetSpy: ReturnType<typeof vi.spyOn>

    beforeEach(() => {
      const fakeResponse = {
        data: new Blob(['id,operation\n1,CREATE'], { type: 'text/csv' }),
        headers: {},
      }
      apiGetSpy = vi.spyOn(apiModule.apiClient, 'get').mockResolvedValue(fakeResponse)

      vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:http://localhost/mock-url')
      vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined)

      const mockLink = {
        href: '',
        download: '',
        click: vi.fn(),
        remove: vi.fn(),
        setAttribute: vi.fn(),
      }
      vi.spyOn(document, 'createElement').mockReturnValue(mockLink as unknown as HTMLElement)
      vi.spyOn(document.body, 'appendChild').mockImplementation(() => mockLink as unknown as Node)
    })

    afterEach(() => {
      vi.restoreAllMocks()
    })

    it('calls GET /audit-logs/export with blob responseType', async () => {
      await exportAuditLogs('csv', {})

      expect(apiGetSpy).toHaveBeenCalledWith(
        '/audit-logs/export',
        expect.objectContaining({ responseType: 'blob' })
      )
    })

    it('passes format param in the request', async () => {
      await exportAuditLogs('csv', {})

      expect(apiGetSpy).toHaveBeenCalledWith(
        '/audit-logs/export',
        expect.objectContaining({
          params: expect.objectContaining({ format: 'csv' }),
        })
      )
    })

    it('passes json format param when requested', async () => {
      await exportAuditLogs('json', {})

      expect(apiGetSpy).toHaveBeenCalledWith(
        '/audit-logs/export',
        expect.objectContaining({
          params: expect.objectContaining({ format: 'json' }),
        })
      )
    })

    it('merges filter params with format param', async () => {
      await exportAuditLogs('csv', { account_id: 'AB1234', operation: 'DELETE' })

      expect(apiGetSpy).toHaveBeenCalledWith(
        '/audit-logs/export',
        expect.objectContaining({
          params: expect.objectContaining({
            format: 'csv',
            account_id: 'AB1234',
            operation: 'DELETE',
          }),
        })
      )
    })

    it('triggers a file download link click', async () => {
      const mockLink = {
        href: '',
        download: '',
        click: vi.fn(),
        remove: vi.fn(),
        setAttribute: vi.fn(),
      }
      vi.spyOn(document, 'createElement').mockReturnValue(mockLink as unknown as HTMLElement)
      vi.spyOn(document.body, 'appendChild').mockImplementation(() => mockLink as unknown as Node)

      await exportAuditLogs('csv', {})

      expect(mockLink.click).toHaveBeenCalled()
    })
  })
})
