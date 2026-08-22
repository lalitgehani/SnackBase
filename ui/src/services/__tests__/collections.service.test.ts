import { describe, it, expect, vi } from 'vitest'
import { createCollectionsService } from '../collections.service'

describe('createCollectionsService', () => {
  it('getCollections delegates to client.collections.listPaginated', async () => {
    const listPaginated = vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 25, total_pages: 0 })
    const client = {
      collections: { listPaginated, get: vi.fn(), create: vi.fn(), update: vi.fn(), delete: vi.fn(), export: vi.fn(), import: vi.fn() },
      collectionRules: { get: vi.fn(), update: vi.fn() },
    } as unknown as Parameters<typeof createCollectionsService>[0]

    const service = createCollectionsService(client)
    await service.getCollections({ page: 1 })

    expect(listPaginated).toHaveBeenCalledWith({ page: 1 })
  })
})
