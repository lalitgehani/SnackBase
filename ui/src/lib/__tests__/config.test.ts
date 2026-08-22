import { afterEach, describe, it, expect } from 'vitest'
import {
  loadConfig,
  platformBaseUrl,
  DEFAULT_SNACKBASE_URL,
  DEFAULT_PROVISION_API_URL,
  DEFAULT_PLATFORM_PATH_PREFIX,
  runtimeApiBaseUrl,
  runtimeSnackbaseUrl,
  runtimeProvisionApiUrl,
} from '../config'

describe('loadConfig', () => {
  afterEach(() => {
    delete window.__SNACKBASE_ENV__
  })

  it('uses self-host defaults when env is empty', () => {
    expect(loadConfig({})).toEqual({
      apiBaseUrl: window.location.origin,
      platformPathPrefix: DEFAULT_PLATFORM_PATH_PREFIX,
      snackbaseUrl: DEFAULT_SNACKBASE_URL,
      provisionApiUrl: DEFAULT_PROVISION_API_URL,
    })
  })

  it('reads VITE_API_BASE_URL and strips trailing slash', () => {
    expect(loadConfig({ VITE_API_BASE_URL: 'https://api.example.com/' })).toEqual({
      apiBaseUrl: 'https://api.example.com',
      platformPathPrefix: DEFAULT_PLATFORM_PATH_PREFIX,
      snackbaseUrl: DEFAULT_SNACKBASE_URL,
      provisionApiUrl: DEFAULT_PROVISION_API_URL,
    })
  })

  it('reads VITE_SNACKBASE_URL and VITE_PROVISION_API_URL', () => {
    expect(
      loadConfig({
        VITE_SNACKBASE_URL: 'https://cp.example.com/',
        VITE_PROVISION_API_URL: 'http://localhost:8091/',
      }),
    ).toEqual({
      apiBaseUrl: window.location.origin,
      platformPathPrefix: DEFAULT_PLATFORM_PATH_PREFIX,
      snackbaseUrl: 'https://cp.example.com',
      provisionApiUrl: 'http://localhost:8091',
    })
  })

  it('prefers runtime window.__SNACKBASE_ENV__ over Vite env', () => {
    window.__SNACKBASE_ENV__ = {
      apiBaseUrl: 'https://runtime.example.com/',
      snackbaseUrl: 'https://api.cloud.example.com/',
      provisionApiUrl: 'https://provision.cloud.example.com/',
    }
    expect(
      loadConfig({
        VITE_API_BASE_URL: 'http://localhost:8000',
        VITE_SNACKBASE_URL: 'http://localhost:8002',
      }),
    ).toEqual({
      apiBaseUrl: 'https://runtime.example.com',
      platformPathPrefix: DEFAULT_PLATFORM_PATH_PREFIX,
      snackbaseUrl: 'https://api.cloud.example.com',
      provisionApiUrl: 'https://provision.cloud.example.com',
    })
  })

  it('can ignore runtime when preferRuntime is false', () => {
    window.__SNACKBASE_ENV__ = {
      apiBaseUrl: 'https://runtime.example.com',
      snackbaseUrl: 'https://api.cloud.example.com',
      provisionApiUrl: 'https://provision.cloud.example.com',
    }
    expect(
      loadConfig(
        {
          VITE_API_BASE_URL: 'http://localhost:8000',
          VITE_SNACKBASE_URL: 'http://localhost:8002',
          VITE_PROVISION_API_URL: 'http://localhost:8091',
        },
        { preferRuntime: false },
      ),
    ).toEqual({
      apiBaseUrl: 'http://localhost:8000',
      platformPathPrefix: DEFAULT_PLATFORM_PATH_PREFIX,
      snackbaseUrl: 'http://localhost:8002',
      provisionApiUrl: 'http://localhost:8091',
    })
  })
})

describe('platformBaseUrl', () => {
  it('composes prefix, env, and ref without double slashes', () => {
    const config = {
      apiBaseUrl: window.location.origin,
      platformPathPrefix: '/platform/v1',
    }
    expect(platformBaseUrl('abcdefghijklmnopqrst', config)).toBe(
      `${window.location.origin}/platform/v1/env/abcdefghijklmnopqrst`,
    )
  })
})

describe('runtime helpers', () => {
  it('returns null when unset', () => {
    expect(runtimeApiBaseUrl({})).toBeNull()
    expect(runtimeSnackbaseUrl({})).toBeNull()
    expect(runtimeProvisionApiUrl({})).toBeNull()
  })

  it('normalizes trailing slash', () => {
    expect(
      runtimeSnackbaseUrl({
        __SNACKBASE_ENV__: { snackbaseUrl: 'https://api.example.com/' },
      }),
    ).toBe('https://api.example.com')
  })
})
