/** 20 lowercase alphanumeric characters — stable environment URL identity. */
export const ENV_REF_LENGTH = 20
export const ENV_REF_PATTERN = /^[a-z0-9]{20}$/
const ENV_REF_ALPHABET = 'abcdefghijklmnopqrstuvwxyz0123456789'

export function generateEnvironmentRef(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(ENV_REF_LENGTH))
  let out = ''
  for (let i = 0; i < ENV_REF_LENGTH; i++) {
    out += ENV_REF_ALPHABET[bytes[i]! % ENV_REF_ALPHABET.length]
  }
  return out
}

export function isValidEnvironmentRef(value: unknown): value is string {
  return typeof value === 'string' && ENV_REF_PATTERN.test(value)
}

interface SnackBaseLikeError extends Error {
  status?: number
}

function isRefCollisionError(err: unknown): boolean {
  const msg = String(err instanceof Error ? err.message : err).toLowerCase()
  const status = (err as SnackBaseLikeError)?.status
  return status === 409 || msg.includes('409') || msg.includes('unique') || msg.includes('duplicate')
}

/**
 * Create an environment record, regenerating `ref` on uniqueness collision (max 3 tries).
 */
export async function createEnvironmentWithRef<T extends { ref?: string }>(
  create: (payload: Record<string, unknown>) => Promise<T>,
  payload: Record<string, unknown>,
  maxAttempts = 3,
): Promise<T> {
  let lastError: unknown
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      return await create({ ...payload, ref: generateEnvironmentRef() })
    } catch (err) {
      lastError = err
      if (!isRefCollisionError(err) || attempt === maxAttempts - 1) {
        throw err
      }
    }
  }
  throw lastError instanceof Error ? lastError : new Error(String(lastError))
}

/** Route/proxy identity for an environment (never use slug — not globally unique). */
export function environmentRouteRef(env: { ref?: string | null; id: string }): string {
  if (isValidEnvironmentRef(env.ref)) return env.ref
  return env.id
}

/** Filter expression to resolve an environment from a URL ref segment. */
export function environmentRefLookupFilter(ref: string): string {
  const trimmed = ref.trim()
  if (isValidEnvironmentRef(trimmed)) {
    return `ref = "${trimmed}"`
  }
  return `ref = "${trimmed}" || id = "${trimmed}"`
}
