import type { ReactNode } from 'react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ThemeProvider } from '@/components/theme-provider'
import { ModeToggle, ThemeMenuItems } from '@/components/mode-toggle'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'

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

describe('ModeToggle', () => {
  beforeEach(() => {
    localStorage.removeItem(STORAGE_KEY)
    document.documentElement.classList.remove('dark')
    mockMatchMedia(false)
  })

  it('exposes an accessible toggle trigger', async () => {
    renderWithTheme(<ModeToggle />, { defaultTheme: 'light' })

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /toggle theme/i }),
      ).not.toBeDisabled()
    })
  })

  it('selecting Dark applies dark class and persists preference', async () => {
    const user = userEvent.setup()
    renderWithTheme(<ModeToggle />, { defaultTheme: 'light' })

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /toggle theme/i }),
      ).not.toBeDisabled()
    })

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

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /toggle theme/i }),
      ).not.toBeDisabled()
    })

    await user.click(screen.getByRole('button', { name: /toggle theme/i }))
    await user.click(await screen.findByRole('menuitemradio', { name: /light/i }))

    await waitFor(() => {
      expect(document.documentElement.classList.contains('dark')).toBe(false)
      expect(localStorage.getItem(STORAGE_KEY)).toBe('light')
    })
  })

  it('selecting System follows OS preference and persists', async () => {
    const user = userEvent.setup()
    mockMatchMedia(true) // OS prefers dark

    renderWithTheme(<ModeToggle />, { defaultTheme: 'light' })

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /toggle theme/i }),
      ).not.toBeDisabled()
    })

    await user.click(screen.getByRole('button', { name: /toggle theme/i }))
    await user.click(
      await screen.findByRole('menuitemradio', { name: /system/i }),
    )

    await waitFor(() => {
      expect(localStorage.getItem(STORAGE_KEY)).toBe('system')
      expect(document.documentElement.classList.contains('dark')).toBe(true)
    })
  })

  it('indicates the active preference with a radio check', async () => {
    const user = userEvent.setup()
    renderWithTheme(<ModeToggle />, { defaultTheme: 'light' })

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /toggle theme/i }),
      ).not.toBeDisabled()
    })

    await user.click(screen.getByRole('button', { name: /toggle theme/i }))

    const lightItem = await screen.findByRole('menuitemradio', {
      name: /light/i,
    })
    expect(lightItem).toHaveAttribute('aria-checked', 'true')

    const darkItem = screen.getByRole('menuitemradio', { name: /dark/i })
    expect(darkItem).toHaveAttribute('aria-checked', 'false')
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
