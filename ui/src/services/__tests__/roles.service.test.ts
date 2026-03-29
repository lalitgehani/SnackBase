import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import {
  getRoles,
  getRoleById,
  createRole,
  updateRole,
  deleteRole,
  getRolePermissions,
  getRolePermissionsMatrix,
  validateRule,
  testRule,
  updateRolePermissionsBulk,
  deletePermission,
} from '../roles.service'
import type {
  RoleListResponse,
  Role,
  RolePermissionsResponse,
} from '../roles.service'

const mockRole: Role = {
  id: 1,
  name: 'Admin',
  description: 'Full access administrator',
}

const mockRoleListResponse: RoleListResponse = {
  items: [
    { ...mockRole, collections_count: 3 },
    { id: 2, name: 'Member', description: 'Standard member', collections_count: 1 },
  ],
  total: 2,
}

const mockPermissionsResponse: RolePermissionsResponse = {
  role_id: 1,
  role_name: 'Admin',
  permissions: [
    {
      collection: 'posts',
      permission_id: 10,
      create: { rule: 'true', fields: '*' },
      read: { rule: 'true', fields: '*' },
      update: { rule: 'user.id == record.created_by', fields: '*' },
      delete: { rule: 'false', fields: '*' },
    },
  ],
}

describe('Roles Service', () => {
  describe('getRoles()', () => {
    it('sends GET to /roles', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/roles', () => {
          requestReceived = true
          return HttpResponse.json(mockRoleListResponse)
        })
      )

      await getRoles()
      expect(requestReceived).toBe(true)
    })

    it('returns role list response on success', async () => {
      server.use(
        http.get('/api/v1/roles', () => HttpResponse.json(mockRoleListResponse))
      )

      const result = await getRoles()
      expect(result).toEqual(mockRoleListResponse)
    })

    it('returns items array and total count', async () => {
      server.use(
        http.get('/api/v1/roles', () => HttpResponse.json(mockRoleListResponse))
      )

      const result = await getRoles()
      expect(result.items).toHaveLength(2)
      expect(result.total).toBe(2)
    })

    it('propagates API errors', async () => {
      server.use(
        http.get('/api/v1/roles', () =>
          HttpResponse.json({ detail: 'Forbidden' }, { status: 403 })
        )
      )

      await expect(getRoles()).rejects.toThrow()
    })
  })

  describe('getRoleById()', () => {
    it('sends GET to /roles/{id}', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/roles/1', () => {
          requestReceived = true
          return HttpResponse.json(mockRole)
        })
      )

      await getRoleById(1)
      expect(requestReceived).toBe(true)
    })

    it('returns role on success', async () => {
      server.use(
        http.get('/api/v1/roles/1', () => HttpResponse.json(mockRole))
      )

      const result = await getRoleById(1)
      expect(result).toEqual(mockRole)
    })

    it('propagates 404 when role not found', async () => {
      server.use(
        http.get('/api/v1/roles/9999', () =>
          HttpResponse.json({ detail: 'Role not found' }, { status: 404 })
        )
      )

      await expect(getRoleById(9999)).rejects.toThrow()
    })
  })

  describe('createRole()', () => {
    it('sends POST to /roles with payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/roles', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockRole, { status: 201 })
        })
      )

      await createRole({ name: 'Admin', description: 'Full access administrator' })

      expect(capturedBody).toEqual({ name: 'Admin', description: 'Full access administrator' })
    })

    it('sends POST with name only when description is omitted', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/roles', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json({ ...mockRole, description: null }, { status: 201 })
        })
      )

      await createRole({ name: 'Viewer' })

      expect(capturedBody).toEqual({ name: 'Viewer' })
    })

    it('returns created role on success', async () => {
      server.use(
        http.post('/api/v1/roles', () => HttpResponse.json(mockRole, { status: 201 }))
      )

      const result = await createRole({ name: 'Admin' })
      expect(result).toEqual(mockRole)
    })

    it('propagates API errors on duplicate name', async () => {
      server.use(
        http.post('/api/v1/roles', () =>
          HttpResponse.json({ detail: 'Role name already exists' }, { status: 409 })
        )
      )

      await expect(createRole({ name: 'Admin' })).rejects.toThrow()
    })
  })

  describe('updateRole()', () => {
    it('sends PUT to /roles/{id} with payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.put('/api/v1/roles/1', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json(mockRole)
        })
      )

      await updateRole(1, { name: 'Super Admin', description: 'Updated description' })

      expect(capturedBody).toEqual({ name: 'Super Admin', description: 'Updated description' })
    })

    it('returns updated role on success', async () => {
      const updated = { ...mockRole, name: 'Super Admin' }

      server.use(
        http.put('/api/v1/roles/1', () => HttpResponse.json(updated))
      )

      const result = await updateRole(1, { name: 'Super Admin' })
      expect(result.name).toBe('Super Admin')
    })

    it('propagates 404 when role not found', async () => {
      server.use(
        http.put('/api/v1/roles/9999', () =>
          HttpResponse.json({ detail: 'Role not found' }, { status: 404 })
        )
      )

      await expect(updateRole(9999, { name: 'Ghost' })).rejects.toThrow()
    })
  })

  describe('deleteRole()', () => {
    it('sends DELETE to /roles/{id}', async () => {
      let requestReceived = false

      server.use(
        http.delete('/api/v1/roles/1', () => {
          requestReceived = true
          return new HttpResponse(null, { status: 204 })
        })
      )

      await deleteRole(1)
      expect(requestReceived).toBe(true)
    })

    it('resolves without a return value on success', async () => {
      server.use(
        http.delete('/api/v1/roles/1', () => new HttpResponse(null, { status: 204 }))
      )

      const result = await deleteRole(1)
      expect(result).toBeUndefined()
    })

    it('propagates 404 when role not found', async () => {
      server.use(
        http.delete('/api/v1/roles/9999', () =>
          HttpResponse.json({ detail: 'Role not found' }, { status: 404 })
        )
      )

      await expect(deleteRole(9999)).rejects.toThrow()
    })
  })

  describe('getRolePermissions()', () => {
    it('sends GET to /roles/{id}/permissions', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/roles/1/permissions', () => {
          requestReceived = true
          return HttpResponse.json(mockPermissionsResponse)
        })
      )

      await getRolePermissions(1)
      expect(requestReceived).toBe(true)
    })

    it('returns permissions response on success', async () => {
      server.use(
        http.get('/api/v1/roles/1/permissions', () => HttpResponse.json(mockPermissionsResponse))
      )

      const result = await getRolePermissions(1)
      expect(result).toEqual(mockPermissionsResponse)
    })
  })

  describe('getRolePermissionsMatrix()', () => {
    it('sends GET to /roles/{id}/permissions/matrix', async () => {
      let requestReceived = false

      server.use(
        http.get('/api/v1/roles/1/permissions/matrix', () => {
          requestReceived = true
          return HttpResponse.json(mockPermissionsResponse)
        })
      )

      await getRolePermissionsMatrix(1)
      expect(requestReceived).toBe(true)
    })

    it('returns permissions matrix response on success', async () => {
      server.use(
        http.get('/api/v1/roles/1/permissions/matrix', () =>
          HttpResponse.json(mockPermissionsResponse)
        )
      )

      const result = await getRolePermissionsMatrix(1)
      expect(result.role_id).toBe(1)
      expect(result.permissions).toHaveLength(1)
    })
  })

  describe('validateRule()', () => {
    it('sends POST to /roles/validate-rule with rule payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/roles/validate-rule', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json({ valid: true, error: null })
        })
      )

      await validateRule('user.id == record.created_by')

      expect(capturedBody).toEqual({ rule: 'user.id == record.created_by' })
    })

    it('returns valid: true for a correct rule', async () => {
      server.use(
        http.post('/api/v1/roles/validate-rule', () =>
          HttpResponse.json({ valid: true, error: null })
        )
      )

      const result = await validateRule('true')
      expect(result.valid).toBe(true)
      expect(result.error).toBeNull()
    })

    it('returns valid: false with error for an invalid rule', async () => {
      server.use(
        http.post('/api/v1/roles/validate-rule', () =>
          HttpResponse.json({ valid: false, error: 'Unexpected token' })
        )
      )

      const result = await validateRule('!!!invalid!!!')
      expect(result.valid).toBe(false)
      expect(result.error).toBe('Unexpected token')
    })
  })

  describe('testRule()', () => {
    it('sends POST to /roles/test-rule with rule and context', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.post('/api/v1/roles/test-rule', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json({ allowed: true, error: null, evaluation_details: null })
        })
      )

      const context = { user: { id: 'user-1' }, record: { created_by: 'user-1' } }
      await testRule('user.id == record.created_by', context)

      expect(capturedBody).toEqual({ rule: 'user.id == record.created_by', context })
    })

    it('returns allowed: true when rule passes', async () => {
      server.use(
        http.post('/api/v1/roles/test-rule', () =>
          HttpResponse.json({ allowed: true, error: null, evaluation_details: null })
        )
      )

      const result = await testRule('true', {})
      expect(result.allowed).toBe(true)
    })

    it('returns allowed: false when rule fails', async () => {
      server.use(
        http.post('/api/v1/roles/test-rule', () =>
          HttpResponse.json({ allowed: false, error: null, evaluation_details: 'rule evaluated to false' })
        )
      )

      const result = await testRule('false', {})
      expect(result.allowed).toBe(false)
    })
  })

  describe('updateRolePermissionsBulk()', () => {
    it('sends PUT to /roles/{id}/permissions/bulk with payload', async () => {
      let capturedBody: Record<string, unknown> | null = null

      server.use(
        http.put('/api/v1/roles/1/permissions/bulk', async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>
          return HttpResponse.json({ success_count: 1, failure_count: 0, errors: [] })
        })
      )

      await updateRolePermissionsBulk(1, {
        updates: [
          { collection: 'posts', operation: 'read', rule: 'true', fields: '*' },
        ],
      })

      expect(capturedBody).toMatchObject({
        updates: [{ collection: 'posts', operation: 'read', rule: 'true', fields: '*' }],
      })
    })

    it('returns success count on success', async () => {
      server.use(
        http.put('/api/v1/roles/1/permissions/bulk', () =>
          HttpResponse.json({ success_count: 2, failure_count: 0, errors: [] })
        )
      )

      const result = await updateRolePermissionsBulk(1, { updates: [] })
      expect(result.success_count).toBe(2)
      expect(result.failure_count).toBe(0)
    })
  })

  describe('deletePermission()', () => {
    it('sends DELETE to /permissions/{id}', async () => {
      let requestReceived = false

      server.use(
        http.delete('/api/v1/permissions/10', () => {
          requestReceived = true
          return new HttpResponse(null, { status: 204 })
        })
      )

      await deletePermission(10)
      expect(requestReceived).toBe(true)
    })

    it('resolves without a return value on success', async () => {
      server.use(
        http.delete('/api/v1/permissions/10', () => new HttpResponse(null, { status: 204 }))
      )

      const result = await deletePermission(10)
      expect(result).toBeUndefined()
    })
  })
})
