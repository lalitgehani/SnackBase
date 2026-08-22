import { describe, it, expect, vi } from 'vitest'
import { createOrganization } from './create-organization'
import type { SnackBaseClient } from '@snackbase/sdk'

describe('createOrganization', () => {
  it('creates with active status', async () => {
    const create = vi.fn(async (_c: string, data: unknown) => ({
      id: 'o1',
      ...(data as object),
    }))
    const client = { records: { create } } as unknown as SnackBaseClient
    const result = await createOrganization(client, {
      name: 'Acme',
      slug: 'acme',
    })
    expect(result.organization.slug).toBe('acme')
    expect(create).toHaveBeenCalledWith('organizations', {
      name: 'Acme',
      slug: 'acme',
      status: 'active',
    })
  })

  it('rejects invalid slug', async () => {
    const client = {
      records: { create: vi.fn() },
    } as unknown as SnackBaseClient
    await expect(
      createOrganization(client, { name: 'Acme', slug: 'Bad Slug' }),
    ).rejects.toThrow(/lowercase/i)
  })

  it('maps duplicate slug errors', async () => {
    const client = {
      records: {
        create: vi.fn(async () => {
          throw new Error('duplicate key unique')
        }),
      },
    } as unknown as SnackBaseClient
    await expect(
      createOrganization(client, { name: 'Acme', slug: 'acme' }),
    ).rejects.toThrow(/already exists/i)
  })
})
