import { describe, it, expect, vi } from 'vitest'
import { createAuditService } from '../audit.service'

describe('createAuditService', () => {
  it('getAuditLogs delegates to client.auditLogs.list', async () => {
    const list = vi.fn().mockResolvedValue({ items: [], total: 0, skip: 0, limit: 25 })
    const client = {
      auditLogs: { list, get: vi.fn(), export: vi.fn() },
    } as unknown as Parameters<typeof createAuditService>[0]

    const service = createAuditService(client)
    await service.getAuditLogs({ limit: 25 })

    expect(list).toHaveBeenCalledWith({ limit: 25 })
  })
})
