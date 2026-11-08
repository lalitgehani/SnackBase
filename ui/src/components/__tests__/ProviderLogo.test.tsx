import { afterEach, describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ProviderLogo } from '@/components/common/ProviderLogo'

describe('ProviderLogo', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('loads API logo paths through the admin app base path', () => {
    // Vitest does not apply vite.config's `base` to import.meta.env, so stub
    // the production admin base explicitly.
    vi.stubEnv('BASE_URL', '/_/')

    render(<ProviderLogo logoUrl="/assets/providers/system.svg" providerName="local" />)

    const logo = screen.getByRole('img', { name: 'local logo' })
    const style = logo.getAttribute('style') ?? ''
    expect(style).toContain('/_/assets/providers/system.svg')
    expect(style).not.toContain('url(/assets/providers/system.svg)')
  })

  it('falls back to the settings icon when no logo is configured', () => {
    render(<ProviderLogo logoUrl={null} providerName="local" />)

    expect(screen.queryByRole('img', { name: 'local logo' })).not.toBeInTheDocument()
  })
})
