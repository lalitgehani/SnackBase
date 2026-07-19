import type { ReactNode } from 'react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import { useTheme } from 'next-themes'
import { ThemeProvider } from '@/components/theme-provider'

const STORAGE_KEY = 'snackbase.theme'

function mockMatchMedia(matches: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })
}

function ThemeProbe() {
  const { theme, setTheme, resolvedTheme } = useTheme()
  return (
    <div>
      <span data-testid="theme">{theme ?? 'undefined'}</span>
      <span data-testid="resolved">{resolvedTheme ?? 'undefined'}</span>
      <button type="button" onClick={() => setTheme('dark')}>
        set-dark
      </button>
      <button type="button" onClick={() => setTheme('light')}>
        set-light
      </button>
      <button type="button" onClick={() => setTheme('system')}>
        set-system
      </button>
    </div>
  )
}

function renderWithTheme(
  ui: ReactNode,
  options?: { defaultTheme?: string },
) {
  return render(
    <ThemeProvider
      attribute="class"
      defaultTheme={options?.defaultTheme ?? 'system'}
      enableSystem
      storageKey={STORAGE_KEY}
      disableTransitionOnChange
    >
      {ui}
    </ThemeProvider>,
  )
}

describe('ThemeProvider', () => {
  beforeEach(() => {
    localStorage.removeItem(STORAGE_KEY)
    document.documentElement.classList.remove('dark')
    mockMatchMedia(false)
  })

  it('provides useTheme context to children', async () => {
    renderWithTheme(<ThemeProbe />, { defaultTheme: 'light' })

    await waitFor(() => {
      expect(screen.getByTestId('theme')).not.toHaveTextContent('undefined')
    })

    expect(screen.getByTestId('theme')).toHaveTextContent('light')
  })

  it('setTheme("dark") applies dark class and persists preference', async () => {
    renderWithTheme(<ThemeProbe />, { defaultTheme: 'light' })

    await waitFor(() => {
      expect(screen.getByTestId('theme')).toHaveTextContent('light')
    })

    await act(async () => {
      screen.getByRole('button', { name: 'set-dark' }).click()
    })

    await waitFor(() => {
      expect(screen.getByTestId('theme')).toHaveTextContent('dark')
      expect(document.documentElement.classList.contains('dark')).toBe(true)
    })

    expect(localStorage.getItem(STORAGE_KEY)).toBe('dark')
  })

  it('setTheme("light") removes dark class and persists preference', async () => {
    localStorage.setItem(STORAGE_KEY, 'dark')
    document.documentElement.classList.add('dark')

    renderWithTheme(<ThemeProbe />, { defaultTheme: 'dark' })

    await waitFor(() => {
      expect(screen.getByTestId('theme')).toHaveTextContent('dark')
    })

    await act(async () => {
      screen.getByRole('button', { name: 'set-light' }).click()
    })

    await waitFor(() => {
      expect(screen.getByTestId('theme')).toHaveTextContent('light')
      expect(document.documentElement.classList.contains('dark')).toBe(false)
    })

    expect(localStorage.getItem(STORAGE_KEY)).toBe('light')
  })
})
