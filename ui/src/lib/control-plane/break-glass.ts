/**
 * Break-glass instance access via the platform gateway.
 */

import { loadConfig, platformBaseUrl } from '@/lib/config'

export interface BreakGlassCredentials {
  instance_url: string
  email: string
  password: string
}

/**
 * POST /platform/v1/env/{ref}/_platform/break-glass
 */
export async function invokeBreakGlass(input: {
  envRef: string
  accessToken: string
}): Promise<BreakGlassCredentials> {
  const ref = input.envRef.trim()
  if (!ref) throw new Error('Environment ref is required')
  if (!input.accessToken.trim()) throw new Error('Access token is required')

  const { apiBaseUrl, platformPathPrefix } = loadConfig()
  const base = platformBaseUrl(ref, { apiBaseUrl, platformPathPrefix })
  const res = await fetch(`${base}/_platform/break-glass`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      Authorization: `Bearer ${input.accessToken}`,
    },
  })

  const text = await res.text()
  let data: Record<string, unknown> = {}
  if (text) {
    try {
      data = JSON.parse(text) as Record<string, unknown>
    } catch {
      data = { error: text }
    }
  }

  if (!res.ok) {
    const msg =
      (typeof data.error === 'string' && data.error) ||
      (typeof data.code === 'string' && data.code) ||
      `Break-glass failed (${res.status})`
    throw new Error(msg)
  }

  return {
    instance_url: String(data.instance_url || ''),
    email: String(data.email || ''),
    password: String(data.password || ''),
  }
}
