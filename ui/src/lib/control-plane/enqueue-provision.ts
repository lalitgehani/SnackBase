/**
 * Enqueue a provision job (worker generates instance credentials at claim time).
 */

export interface EnqueueProvisionInput {
  environmentId: string
  /** Bearer access token from AuthManager */
  accessToken: string
  /** Provision enqueue API base URL */
  provisionApiUrl: string
}

export interface EnqueueProvisionResult {
  job_id: string
  environment_id: string
  email: string
}

/**
 * POST /v1/provision-jobs on the provision-enqueue service.
 */
export async function enqueueProvisionJob(
  input: EnqueueProvisionInput,
): Promise<EnqueueProvisionResult> {
  const base = input.provisionApiUrl.replace(/\/$/, '')
  const environmentId = input.environmentId.trim()
  if (!environmentId) throw new Error('Environment id is required')
  if (!input.accessToken.trim()) throw new Error('Access token is required')

  const res = await fetch(`${base}/v1/provision-jobs`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      Authorization: `Bearer ${input.accessToken}`,
    },
    body: JSON.stringify({
      environment_id: environmentId,
    }),
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
      (typeof data.message === 'string' && data.message) ||
      `Enqueue failed (${res.status})`
    throw new Error(msg)
  }

  return {
    job_id: String(data.job_id || ''),
    environment_id: String(data.environment_id || environmentId),
    email: String(data.email || ''),
  }
}
