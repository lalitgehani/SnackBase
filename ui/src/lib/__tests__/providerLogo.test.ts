import { describe, it, expect } from 'vitest'
import { resolveProviderLogoUrl } from '../providerLogo'

describe('resolveProviderLogoUrl', () => {
  it('returns undefined for empty values', () => {
    expect(resolveProviderLogoUrl(undefined, '/_/')).toBeUndefined()
    expect(resolveProviderLogoUrl(null, '/_/')).toBeUndefined()
    expect(resolveProviderLogoUrl('', '/_/')).toBeUndefined()
  })

  it('prefixes root-absolute provider paths with the app base', () => {
    expect(resolveProviderLogoUrl('/assets/providers/system.svg', '/_/')).toBe(
      '/_/assets/providers/system.svg',
    )
  })

  it('normalizes a base without a trailing slash', () => {
    expect(resolveProviderLogoUrl('/assets/providers/okta.svg', '/_')).toBe(
      '/_/assets/providers/okta.svg',
    )
  })

  it('leaves paths untouched when the app is served from the root', () => {
    expect(resolveProviderLogoUrl('/assets/providers/smtp.svg', '/')).toBe(
      '/assets/providers/smtp.svg',
    )
  })

  it('does not double-prefix a path that already carries the base', () => {
    expect(resolveProviderLogoUrl('/_/assets/providers/azure.svg', '/_/')).toBe(
      '/_/assets/providers/azure.svg',
    )
  })

  it('keeps external, protocol-relative, data, and relative URLs as-is', () => {
    expect(resolveProviderLogoUrl('https://cdn.example.com/logo.svg', '/_/')).toBe(
      'https://cdn.example.com/logo.svg',
    )
    expect(resolveProviderLogoUrl('//cdn.example.com/logo.svg', '/_/')).toBe(
      '//cdn.example.com/logo.svg',
    )
    expect(resolveProviderLogoUrl('data:image/svg+xml;base64,abc', '/_/')).toBe(
      'data:image/svg+xml;base64,abc',
    )
    expect(resolveProviderLogoUrl('logo.svg', '/_/')).toBe('logo.svg')
  })
})
