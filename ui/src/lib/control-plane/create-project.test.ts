import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createProject } from './create-project'
import type { SnackBaseClient } from '@snackbase/sdk'

function mockClient(overrides?: {
  regions?: { code: string; label?: string; metadata?: Record<string, unknown> }[]
  createProject?: () => Promise<unknown>
  createEnv?: () => Promise<unknown>
  deleteProject?: () => Promise<unknown>
}) {
  const create = vi.fn(async (collection: string, data: unknown) => {
    if (collection === 'projects') {
      if (overrides?.createProject) return overrides.createProject()
      return { id: 'proj-1', ...(data as object) }
    }
    if (collection === 'environments') {
      if (overrides?.createEnv) return overrides.createEnv()
      return { id: 'env-1', ...(data as object) }
    }
    throw new Error(`unexpected collection ${collection}`)
  })
  const del = vi.fn(async () => {
    if (overrides?.deleteProject) return overrides.deleteProject()
  })
  const getValues = vi.fn(async () =>
    (overrides?.regions ?? [
      {
        code: 'eu-01',
        label: 'EU',
        metadata: { country: 'DE', status: 'available' },
      },
    ]).map((r) => ({
      code: r.code,
      label: r.label ?? r.code,
      metadata: r.metadata ?? { status: 'available' },
      sort_order: 1,
    })),
  )

  return {
    records: { create, delete: del },
    codelists: { getValues },
  } as unknown as SnackBaseClient
}

const baseInput = () => ({
  organizationId: 'org-1',
  name: 'API',
  slug: 'my-api',
  region: 'eu-01',
  tenancyMode: 'single' as const,
})

describe('createProject', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('creates project and production environment without bootstrap secrets', async () => {
    const client = mockClient()
    const input = baseInput()
    const result = await createProject(client, input)

    expect(result.project.id).toBe('proj-1')
    expect(result.environment.slug).toBe('production')
    expect(result.environment.status).toBe('pending')
    expect(client.records.create).toHaveBeenCalledTimes(2)
    expect(client.records.create).toHaveBeenCalledWith(
      'environments',
      expect.objectContaining({
        slug: 'production',
        status: 'pending',
        region: 'eu-01',
      }),
    )
    const envPayload = vi.mocked(client.records.create).mock.calls.find(
      (c) => c[0] === 'environments',
    )?.[1] as Record<string, unknown>
    expect(envPayload.snackbase_secret_key).toBeUndefined()
  })

  it('rejects missing region', async () => {
    const client = mockClient()
    await expect(
      createProject(client, {
        ...baseInput(),
        region: '',
        tenancyMode: 'multi',
      }),
    ).rejects.toThrow(/region is required/i)
  })

  it('rejects unavailable region', async () => {
    const client = mockClient({
      regions: [
        {
          code: 'eu-01',
          label: 'EU',
          metadata: { status: 'unavailable' },
        },
      ],
    })
    await expect(createProject(client, baseInput())).rejects.toThrow(
      /not available/i,
    )
  })

  it('rejects invalid tenancy mode', async () => {
    const client = mockClient()
    await expect(
      createProject(client, {
        ...baseInput(),
        tenancyMode: 'shared' as 'single',
      }),
    ).rejects.toThrow(/tenancy mode/i)
  })

  it('maps duplicate slug errors', async () => {
    const client = mockClient({
      createProject: async () => {
        throw new Error('UNIQUE constraint failed: projects.slug')
      },
    })
    await expect(
      createProject(client, {
        ...baseInput(),
        slug: 'taken',
      }),
    ).rejects.toThrow(/globally unique/i)
  })

  it('compensates when environment create fails', async () => {
    const client = mockClient({
      createEnv: async () => {
        throw new Error('env boom')
      },
    })
    await expect(createProject(client, baseInput())).rejects.toThrow(
      /production environment failed/i,
    )
    expect(client.records.delete).toHaveBeenCalledWith('projects', 'proj-1')
  })
})
