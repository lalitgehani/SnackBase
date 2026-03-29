import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import {
  getGroups,
  getGroup,
  createGroup,
  updateGroup,
  deleteGroup,
  addUserToGroup,
  removeUserFromGroup,
} from '../groups.service'
import type { Group, GroupListResponse } from '../groups.service'

const mockGroup: Group = {
  id: 'group-1',
  account_id: 'AB1234',
  name: 'Engineering',
  description: 'Engineering team',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  member_count: 3,
}

const mockGroupListResponse: GroupListResponse = {
  items: [
    mockGroup,
    {
      id: 'group-2',
      account_id: 'AB1234',
      name: 'Marketing',
      description: null,
      created_at: '2024-02-01T00:00:00Z',
      updated_at: '2024-02-01T00:00:00Z',
      member_count: 2,
    },
  ],
  total: 2,
}

describe('Groups Service', () => {
  describe('getGroups()', () => {
    it('sends GET to /groups', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/groups', () => {
          requestReceived = true
          return HttpResponse.json(mockGroupListResponse)
        })
      )

      await getGroups()
      expect(requestReceived).toBe(true)
    })

    it('returns group list response on success', async () => {
      server.use(
        http.get('/api/v1/groups', () => HttpResponse.json(mockGroupListResponse))
      )

      const result = await getGroups()
      expect(result).toEqual(mockGroupListResponse)
    })

    it('wraps array response into GroupListResponse shape', async () => {
      server.use(
        http.get('/api/v1/groups', () => HttpResponse.json([mockGroup]))
      )

      const result = await getGroups()
      expect(result.items).toEqual([mockGroup])
      expect(result.total).toBe(1)
    })

    it('passes skip and limit params', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/groups', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockGroupListResponse)
        })
      )

      await getGroups({ skip: 10, limit: 5 })

      expect(capturedUrl).toContain('skip=10')
      expect(capturedUrl).toContain('limit=5')
    })

    it('passes search param', async () => {
      let capturedUrl: string | null = null

      server.use(
        http.get('/api/v1/groups', ({ request }) => {
          capturedUrl = request.url
          return HttpResponse.json(mockGroupListResponse)
        })
      )

      await getGroups({ search: 'engineering' })

      expect(capturedUrl).toContain('search=engineering')
    })

    it('propagates API errors', async () => {
      server.use(
        http.get('/api/v1/groups', () =>
          HttpResponse.json({ detail: 'Forbidden' }, { status: 403 })
        )
      )

      await expect(getGroups()).rejects.toThrow()
    })
  })

  describe('getGroup()', () => {
    it('sends GET to /groups/{id}', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/groups/group-1', () => {
          requestReceived = true
          return HttpResponse.json(mockGroup)
        })
      )

      await getGroup('group-1')
      expect(requestReceived).toBe(true)
    })

    it('returns group on success', async () => {
      server.use(
        http.get('/api/v1/groups/group-1', () => HttpResponse.json(mockGroup))
      )

      const result = await getGroup('group-1')
      expect(result).toEqual(mockGroup)
    })

    it('propagates 404 when group not found', async () => {
      server.use(
        http.get('/api/v1/groups/nonexistent', () =>
          HttpResponse.json({ detail: 'Group not found' }, { status: 404 })
        )
      )

      await expect(getGroup('nonexistent')).rejects.toThrow()
    })
  })

  describe('createGroup()', () => {
    it('sends POST to /groups with payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/groups', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockGroup, { status: 201 })
        })
      )

      await createGroup({ name: 'Engineering', description: 'Engineering team' })

      expect(capturedBody).toEqual({ name: 'Engineering', description: 'Engineering team' })
    })

    it('sends POST with account_id when provided', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/groups', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockGroup, { status: 201 })
        })
      )

      await createGroup({ name: 'Engineering', account_id: 'AB1234' })

      expect(capturedBody).toMatchObject({ account_id: 'AB1234' })
    })

    it('returns created group on success', async () => {
      server.use(
        http.post('/api/v1/groups', () => HttpResponse.json(mockGroup, { status: 201 }))
      )

      const result = await createGroup({ name: 'Engineering' })
      expect(result).toEqual(mockGroup)
    })

    it('propagates API errors on duplicate name', async () => {
      server.use(
        http.post('/api/v1/groups', () =>
          HttpResponse.json({ detail: 'Group name already exists' }, { status: 409 })
        )
      )

      await expect(createGroup({ name: 'Engineering' })).rejects.toThrow()
    })
  })

  describe('updateGroup()', () => {
    it('sends PATCH to /groups/{id} with payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.patch('/api/v1/groups/group-1', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockGroup)
        })
      )

      await updateGroup('group-1', { name: 'Engineering Updated', description: 'Updated desc' })

      expect(capturedBody).toEqual({ name: 'Engineering Updated', description: 'Updated desc' })
    })

    it('returns updated group on success', async () => {
      const updated = { ...mockGroup, name: 'Engineering Updated' }

      server.use(
        http.patch('/api/v1/groups/group-1', () => HttpResponse.json(updated))
      )

      const result = await updateGroup('group-1', { name: 'Engineering Updated' })
      expect(result.name).toBe('Engineering Updated')
    })

    it('propagates 404 when group not found', async () => {
      server.use(
        http.patch('/api/v1/groups/nonexistent', () =>
          HttpResponse.json({ detail: 'Group not found' }, { status: 404 })
        )
      )

      await expect(updateGroup('nonexistent', { name: 'Ghost' })).rejects.toThrow()
    })
  })

  describe('deleteGroup()', () => {
    it('sends DELETE to /groups/{id}', async () => {
      let requestReceived = false

      server.use(
        http.delete('/api/v1/groups/group-1', () => {
          requestReceived = true
          return new HttpResponse(null, { status: 204 })
        })
      )

      await deleteGroup('group-1')
      expect(requestReceived).toBe(true)
    })

    it('resolves without a return value on success', async () => {
      server.use(
        http.delete('/api/v1/groups/group-1', () => new HttpResponse(null, { status: 204 }))
      )

      const result = await deleteGroup('group-1')
      expect(result).toBeUndefined()
    })

    it('propagates 404 when group not found', async () => {
      server.use(
        http.delete('/api/v1/groups/nonexistent', () =>
          HttpResponse.json({ detail: 'Group not found' }, { status: 404 })
        )
      )

      await expect(deleteGroup('nonexistent')).rejects.toThrow()
    })
  })

  describe('addUserToGroup()', () => {
    it('sends POST to /groups/{groupId}/users with user_id payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/groups/group-1/users', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return new HttpResponse(null, { status: 204 })
        })
      )

      await addUserToGroup('group-1', 'user-1')

      expect(capturedBody).toEqual({ user_id: 'user-1' })
    })

    it('resolves without a return value on success', async () => {
      server.use(
        http.post('/api/v1/groups/group-1/users', () => new HttpResponse(null, { status: 204 }))
      )

      const result = await addUserToGroup('group-1', 'user-1')
      expect(result).toBeUndefined()
    })

    it('propagates 404 when group not found', async () => {
      server.use(
        http.post('/api/v1/groups/nonexistent/users', () =>
          HttpResponse.json({ detail: 'Group not found' }, { status: 404 })
        )
      )

      await expect(addUserToGroup('nonexistent', 'user-1')).rejects.toThrow()
    })
  })

  describe('removeUserFromGroup()', () => {
    it('sends DELETE to /groups/{groupId}/users/{userId}', async () => {
      let requestReceived = false

      server.use(
        http.delete('/api/v1/groups/group-1/users/user-1', () => {
          requestReceived = true
          return new HttpResponse(null, { status: 204 })
        })
      )

      await removeUserFromGroup('group-1', 'user-1')
      expect(requestReceived).toBe(true)
    })

    it('resolves without a return value on success', async () => {
      server.use(
        http.delete('/api/v1/groups/group-1/users/user-1', () =>
          new HttpResponse(null, { status: 204 })
        )
      )

      const result = await removeUserFromGroup('group-1', 'user-1')
      expect(result).toBeUndefined()
    })

    it('propagates 404 when user not in group', async () => {
      server.use(
        http.delete('/api/v1/groups/group-1/users/nonexistent', () =>
          HttpResponse.json({ detail: 'User not in group' }, { status: 404 })
        )
      )

      await expect(removeUserFromGroup('group-1', 'nonexistent')).rejects.toThrow()
    })
  })
})
