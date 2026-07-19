import type { ReactNode } from 'react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ThemeProvider } from '@/components/theme-provider'
import {
  ModeToggle,
  ThemeMenuItems,
  ThemeToggleButton,
} from '@/components/mode-toggle'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'

/** Must match ThemeProvider storageKey and FOUC script in index.html */
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

function renderWithTheme(ui: ReactNode, options?: { defaultTheme?: string }) {
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

async function waitForThemeToggleReady() {
  await waitFor(() => {
    expect(
      screen.getByRole('button', { name: /toggle theme/i }),
    ).not.toBeDisabled()
  })
}

describe('ModeToggle', () => {
  beforeEach(() => {
    localStorage.removeItem(STORAGE_KEY)
    document.documentElement.classList.remove('dark')
    mockMatchMedia(false)
  })

  it('exposes an accessible toggle trigger with name "Toggle theme"', async () => {
    renderWithTheme(<ModeToggle />, { defaultTheme: 'light' })

    const trigger = await screen.findByRole('button', { name: /toggle theme/i })
    await waitFor(() => {
      expect(trigger).not.toBeDisabled()
    })
    expect(trigger).toHaveAttribute('aria-label', 'Toggle theme')
  })

  it('always exposes an accessible name and becomes interactive after mount gate', async () => {
    // Mounted gate avoids theme/icon flicker: first paint may be a disabled
    // placeholder, then the live control. Tests wait for readiness so they
    // do not flake on the first render frame.
    renderWithTheme(<ModeToggle />, { defaultTheme: 'light' })

    const trigger = screen.getByRole('button', { name: /toggle theme/i })
    expect(trigger).toHaveAttribute('aria-label', 'Toggle theme')
    expect(trigger).toHaveTextContent(/toggle theme/i) // sr-only label

    await waitForThemeToggleReady()
    expect(trigger).not.toBeDisabled()
  })

  it('selecting Dark applies dark class and persists preference', async () => {
    const user = userEvent.setup()
    renderWithTheme(<ModeToggle />, { defaultTheme: 'light' })
    await waitForThemeToggleReady()

    await user.click(screen.getByRole('button', { name: /toggle theme/i }))
    await user.click(await screen.findByRole('menuitemradio', { name: /dark/i }))

    await waitFor(() => {
      expect(document.documentElement.classList.contains('dark')).toBe(true)
      expect(localStorage.getItem(STORAGE_KEY)).toBe('dark')
    })
  })

  it('selecting Light removes dark class and persists preference', async () => {
    const user = userEvent.setup()
    localStorage.setItem(STORAGE_KEY, 'dark')
    document.documentElement.classList.add('dark')

    renderWithTheme(<ModeToggle />, { defaultTheme: 'dark' })
    await waitForThemeToggleReady()

    await user.click(screen.getByRole('button', { name: /toggle theme/i }))
    await user.click(await screen.findByRole('menuitemradio', { name: /light/i }))

    await waitFor(() => {
      expect(document.documentElement.classList.contains('dark')).toBe(false)
      expect(localStorage.getItem(STORAGE_KEY)).toBe('light')
    })
  })

  it('selecting System follows OS dark preference and persists', async () => {
    const user = userEvent.setup()
    mockMatchMedia(true) // OS prefers dark

    renderWithTheme(<ModeToggle />, { defaultTheme: 'light' })
    await waitForThemeToggleReady()

    await user.click(screen.getByRole('button', { name: /toggle theme/i }))
    await user.click(
      await screen.findByRole('menuitemradio', { name: /system/i }),
    )

    await waitFor(() => {
      expect(localStorage.getItem(STORAGE_KEY)).toBe('system')
      expect(document.documentElement.classList.contains('dark')).toBe(true)
    })
  })

  it('selecting System follows OS light preference and persists', async () => {
    const user = userEvent.setup()
    mockMatchMedia(false) // OS prefers light
    localStorage.setItem(STORAGE_KEY, 'dark')
    document.documentElement.classList.add('dark')

    renderWithTheme(<ModeToggle />, { defaultTheme: 'dark' })
    await waitForThemeToggleReady()

    await user.click(screen.getByRole('button', { name: /toggle theme/i }))
    await user.click(
      await screen.findByRole('menuitemradio', { name: /system/i }),
    )

    await waitFor(() => {
      expect(localStorage.getItem(STORAGE_KEY)).toBe('system')
      expect(document.documentElement.classList.contains('dark')).toBe(false)
    })
  })

  it('indicates the active preference with aria-checked (non-color cue)', async () => {
    const user = userEvent.setup()
    renderWithTheme(<ModeToggle />, { defaultTheme: 'light' })
    await waitForThemeToggleReady()

    await user.click(screen.getByRole('button', { name: /toggle theme/i }))

    const lightItem = await screen.findByRole('menuitemradio', {
      name: /light/i,
    })
    expect(lightItem).toHaveAttribute('aria-checked', 'true')

    const darkItem = screen.getByRole('menuitemradio', { name: /dark/i })
    expect(darkItem).toHaveAttribute('aria-checked', 'false')

    const systemItem = screen.getByRole('menuitemradio', { name: /system/i })
    expect(systemItem).toHaveAttribute('aria-checked', 'false')
  })

  it('is operable via keyboard (open menu, select Dark)', async () => {
    const user = userEvent.setup()
    renderWithTheme(<ModeToggle />, { defaultTheme: 'light' })
    await waitForThemeToggleReady()

    const trigger = screen.getByRole('button', { name: /toggle theme/i })
    trigger.focus()
    expect(trigger).toHaveFocus()

    await user.keyboard('{Enter}')
    const darkItem = await screen.findByRole('menuitemradio', { name: /dark/i })
    expect(darkItem).toBeInTheDocument()

    await user.click(darkItem)

    await waitFor(() => {
      expect(localStorage.getItem(STORAGE_KEY)).toBe('dark')
      expect(document.documentElement.classList.contains('dark')).toBe(true)
    })
  })

  it('ThemeToggleButton is an alias of ModeToggle', async () => {
    renderWithTheme(<ThemeToggleButton />, { defaultTheme: 'light' })
    await waitForThemeToggleReady()
    expect(
      screen.getByRole('button', { name: /toggle theme/i }),
    ).toBeInTheDocument()
  })
})

describe('ThemeMenuItems', () => {
  beforeEach(() => {
    localStorage.removeItem(STORAGE_KEY)
    document.documentElement.classList.remove('dark')
    mockMatchMedia(false)
  })

  it('renders a Theme submenu trigger inside a parent menu', async () => {
    renderWithTheme(
      <DropdownMenu defaultOpen>
        <DropdownMenuTrigger asChild>
          <Button type="button">Account</Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <ThemeMenuItems />
        </DropdownMenuContent>
      </DropdownMenu>,
      { defaultTheme: 'system' },
    )

    const menu = await screen.findByRole('menu')
    expect(within(menu).getByText('Theme')).toBeInTheDocument()
    expect(
      within(menu).getByRole('menuitem', { name: /theme/i }),
    ).toBeInTheDocument()
  })

  it('opens Light / Dark / System options via keyboard', async () => {
    const user = userEvent.setup()

    renderWithTheme(
      <DropdownMenu defaultOpen>
        <DropdownMenuTrigger asChild>
          <Button type="button">Account</Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <ThemeMenuItems />
        </DropdownMenuContent>
      </DropdownMenu>,
      { defaultTheme: 'light' },
    )

    const themeItem = await screen.findByRole('menuitem', { name: /theme/i })
    themeItem.focus()
    await user.keyboard('{ArrowRight}')

    await waitFor(() => {
      expect(
        screen.getByRole('menuitemradio', { name: /light/i }),
      ).toBeInTheDocument()
      expect(
        screen.getByRole('menuitemradio', { name: /dark/i }),
      ).toBeInTheDocument()
      expect(
        screen.getByRole('menuitemradio', { name: /system/i }),
      ).toBeInTheDocument()
    })

    await user.click(screen.getByRole('menuitemradio', { name: /dark/i }))

    await waitFor(() => {
      expect(localStorage.getItem(STORAGE_KEY)).toBe('dark')
      expect(document.documentElement.classList.contains('dark')).toBe(true)
    })
  })
})
