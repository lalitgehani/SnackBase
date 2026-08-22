/**
 * Studio environment configuration.
 * Kept pure so unit tests can pass a mock env map.
 *
 * Resolution order (per field):
 * 1. Runtime `window.__SNACKBASE_ENV__` (Docker/nginx injects `/config.js`)
 * 2. Build-time `VITE_*` (Vite / local `.env`)
 * 3. Defaults for local development
 */

export interface StudioConfig {
  /** Instance API base URL (origin in self-host; proxy prefix in platform) */
  apiBaseUrl: string
  /** Platform gateway path prefix */
  platformPathPrefix: string
  /** Control-plane SnackBase base URL */
  snackbaseUrl: string
  /** Provision enqueue API base URL (Redis job intake) */
  provisionApiUrl: string
}

export interface RuntimeSnackbaseEnv {
  apiBaseUrl?: string
  platformPathPrefix?: string
  snackbaseUrl?: string
  provisionApiUrl?: string
}

declare global {
  interface Window {
    __SNACKBASE_ENV__?: RuntimeSnackbaseEnv
  }
}

/** Build-time platform mode flag — inlined by Vite, not part of loadConfig(). */
export const IS_PLATFORM = import.meta.env.VITE_IS_PLATFORM === 'true'

const DEFAULT_PLATFORM_PATH_PREFIX = '/platform/v1'
const DEFAULT_SNACKBASE_URL = 'http://localhost:8002'
const DEFAULT_PROVISION_API_URL = 'http://localhost:8091'

function normalizeUrl(raw: string | undefined | null): string | null {
  if (typeof raw !== 'string') return null
  const trimmed = raw.trim().replace(/\/$/, '')
  return trimmed.length > 0 ? trimmed : null
}

function defaultApiBaseUrl(): string {
  if (typeof window !== 'undefined' && window.location?.origin) {
    return window.location.origin
  }
  return 'http://localhost'
}

function runtimeEnv(
  win: { __SNACKBASE_ENV__?: RuntimeSnackbaseEnv } | undefined = typeof window !==
  'undefined'
    ? window
    : undefined,
): RuntimeSnackbaseEnv | undefined {
  return win?.__SNACKBASE_ENV__
}

export function runtimeApiBaseUrl(
  win: { __SNACKBASE_ENV__?: RuntimeSnackbaseEnv } | undefined = typeof window !==
  'undefined'
    ? window
    : undefined,
): string | null {
  return normalizeUrl(runtimeEnv(win)?.apiBaseUrl)
}

export function runtimePlatformPathPrefix(
  win: { __SNACKBASE_ENV__?: RuntimeSnackbaseEnv } | undefined = typeof window !==
  'undefined'
    ? window
    : undefined,
): string | null {
  return normalizeUrl(runtimeEnv(win)?.platformPathPrefix)
}

export function runtimeSnackbaseUrl(
  win: { __SNACKBASE_ENV__?: RuntimeSnackbaseEnv } | undefined = typeof window !==
  'undefined'
    ? window
    : undefined,
): string | null {
  return normalizeUrl(runtimeEnv(win)?.snackbaseUrl)
}

export function runtimeProvisionApiUrl(
  win: { __SNACKBASE_ENV__?: RuntimeSnackbaseEnv } | undefined = typeof window !==
  'undefined'
    ? window
    : undefined,
): string | null {
  return normalizeUrl(runtimeEnv(win)?.provisionApiUrl)
}

/**
 * Compose the proxied instance base URL for a given environment ref.
 */
export function platformBaseUrl(
  ref: string,
  config?: Pick<StudioConfig, 'apiBaseUrl' | 'platformPathPrefix'>,
): string {
  const cfg = config ?? loadConfig()
  const prefix = cfg.platformPathPrefix.startsWith('/')
    ? cfg.platformPathPrefix
    : `/${cfg.platformPathPrefix}`
  const origin = cfg.apiBaseUrl.replace(/\/$/, '')
  return `${origin}${prefix}/env/${ref}`
}

/**
 * Load studio config from an env-like object (defaults to `import.meta.env`).
 * When `preferRuntime` is true (default), Docker runtime config wins over Vite env.
 */
export function loadConfig(
  env: Record<string, string | boolean | undefined> = import.meta.env as Record<
    string,
    string | boolean | undefined
  >,
  options: { preferRuntime?: boolean } = {},
): StudioConfig {
  const preferRuntime = options.preferRuntime !== false

  let apiBaseUrl: string | null = null
  let platformPathPrefix: string | null = null
  let snackbaseUrl: string | null = null
  let provisionApiUrl: string | null = null

  if (preferRuntime) {
    apiBaseUrl = runtimeApiBaseUrl()
    platformPathPrefix = runtimePlatformPathPrefix()
    snackbaseUrl = runtimeSnackbaseUrl()
    provisionApiUrl = runtimeProvisionApiUrl()
  }

  if (!apiBaseUrl) {
    apiBaseUrl = normalizeUrl(
      typeof env.VITE_API_BASE_URL === 'string' ? env.VITE_API_BASE_URL : null,
    )
  }
  if (!platformPathPrefix) {
    platformPathPrefix = normalizeUrl(
      typeof env.VITE_PLATFORM_PATH_PREFIX === 'string'
        ? env.VITE_PLATFORM_PATH_PREFIX
        : null,
    )
  }
  if (!snackbaseUrl) {
    snackbaseUrl = normalizeUrl(
      typeof env.VITE_SNACKBASE_URL === 'string' ? env.VITE_SNACKBASE_URL : null,
    )
  }
  if (!provisionApiUrl) {
    provisionApiUrl = normalizeUrl(
      typeof env.VITE_PROVISION_API_URL === 'string'
        ? env.VITE_PROVISION_API_URL
        : null,
    )
  }

  return {
    apiBaseUrl: apiBaseUrl ?? defaultApiBaseUrl(),
    platformPathPrefix: platformPathPrefix ?? DEFAULT_PLATFORM_PATH_PREFIX,
    snackbaseUrl: snackbaseUrl ?? DEFAULT_SNACKBASE_URL,
    provisionApiUrl: provisionApiUrl ?? DEFAULT_PROVISION_API_URL,
  }
}

export {
  DEFAULT_PLATFORM_PATH_PREFIX,
  DEFAULT_SNACKBASE_URL,
  DEFAULT_PROVISION_API_URL,
}
