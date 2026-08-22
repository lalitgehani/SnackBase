import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createEnvironment } from './create-environment'
import type { SnackBaseClient } from '@snackbase/sdk'

function mockClient(overrides?: {
  project?: Record<string, unknown>
  existing?: unknown[]
  create?: () => Promise<unknown>
}) {
  return {
    records: {
      get: vi.fn(async () => ({
        id: 'p1',
        slug: 'my-api',
        name: 'API',
        region: 'eu-01',
        tenancy_mode: 'single',
        ...overrides?.project,
      })),
      list: vi.fn(async () => ({ items: overrides?.existing ?? [] })),
      create: vi.fn(
        async (_c: string, data: unknown) =>
          overrides?.create?.() ?? { id: 'e-new', ...(data as object) },
      ),
    },
  } as unknown as SnackBaseClient
}

describe('createEnvironment', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('creates pending env with project region/tenancy (no bootstrap)', async () => {
    const client = mockClient()
    const env = await createEnvironment(client, {
      projectId: 'p1',
      name: 'Staging',
      slug: 'staging',
    })
    expect(env.slug).toBe('staging')
    expect(env.status).toBe('pending')
    expect(client.records.create).toHaveBeenCalledTimes(1)
    const payload = vi.mocked(client.records.create).mock.calls[0]?.[1] as Record<
      string,
      unknown
    >
    expect(payload.region).toBe('eu-01')
    expect(payload.tenancy_mode).toBe('single')
    expect(payload.status).toBe('pending')
    expect(payload.ref).toMatch(/^[a-z0-9]{20}$/)
    expect(payload.snackbase_secret_key).toBeUndefined()
    expect(payload.snackbase_superadmin_password).toBeUndefined()
  })

  it('rejects duplicate slug', async () => {
    const client = mockClient({
      existing: [{ id: 'e1', slug: 'staging', status: 'ready' }],
    })
    await expect(
      createEnvironment(client, {
        projectId: 'p1',
        name: 'Staging',
        slug: 'staging',
      }),
    ).rejects.toThrow(/already exists/i)
  })

  it('allows reuse of deleted slug', async () => {
    const client = mockClient({
      existing: [{ id: 'e1', slug: 'staging', status: 'deleted' }],
    })
    await expect(
      createEnvironment(client, {
        projectId: 'p1',
        name: 'Staging',
        slug: 'staging',
      }),
    ).resolves.toMatchObject({ slug: 'staging' })
  })
})
