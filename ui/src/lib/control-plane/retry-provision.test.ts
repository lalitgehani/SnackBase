import { describe, it, expect, vi } from 'vitest'
import { retryProvision } from './retry-provision'
import type { SnackBaseClient } from '@snackbase/sdk'

describe('retryProvision', () => {
  it('sets status pending and clears error', async () => {
    const patch = vi.fn(async () => ({
      id: 'e1',
      status: 'pending',
      error_message: null,
    }))
    const client = { records: { patch } } as unknown as SnackBaseClient
    const env = await retryProvision(client, 'e1')
    expect(env.status).toBe('pending')
    expect(patch).toHaveBeenCalledWith('environments', 'e1', {
      status: 'pending',
      error_message: null,
    })
  })
})
