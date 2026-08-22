import { describe, it, expect, vi, afterEach } from 'vitest'
import { enqueueProvisionJob } from './enqueue-provision'

describe('enqueueProvisionJob', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('posts environment_id without password', async () => {
    const fetchMock = vi.fn(async () =>
      new Response(
        JSON.stringify({
          job_id: 'j1',
          environment_id: 'e1',
          email: 'u@example.com',
        }),
        { status: 202 },
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    const result = await enqueueProvisionJob({
      environmentId: 'e1',
      accessToken: 'tok',
      provisionApiUrl: 'http://localhost:8091/',
    })

    expect(result.job_id).toBe('j1')
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8091/v1/provision-jobs',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ environment_id: 'e1' }),
      }),
    )
  })
})
