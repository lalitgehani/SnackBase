import type { APIRequestContext } from '@playwright/test'

/**
 * Delete a collection by name. DELETE /collections/{id} is keyed by collection
 * UUID, so list first and match on `name`.
 */
export async function deleteCollectionByName(
  ctx: APIRequestContext,
  token: string,
  name: string,
) {
  const headers = { Authorization: `Bearer ${token}` }
  const listRes = await ctx.get('/api/v1/collections', {
    headers,
    params: { page_size: 200, search: name },
  })
  if (!listRes.ok()) return

  const body = await listRes.json()
  const items = (body.items ?? []) as Array<{ id: string; name: string }>
  const match = items.find((c) => c.name === name)
  if (!match) return

  await ctx.delete(`/api/v1/collections/${match.id}`, { headers })
}
