import { type ReactElement } from 'react'
import { render, type RenderOptions } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router'

/**
 * Creates a fresh QueryClient per test with retry disabled to avoid
 * async timeout issues in tests.
 */
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })
}

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  /** Initial URL path(s) for MemoryRouter. Defaults to ['/'] */
  initialEntries?: string[]
  /** Pre-configured QueryClient (optional – a fresh one is created by default) */
  queryClient?: QueryClient
}

function AllProviders({
  children,
  initialEntries = ['/'],
  queryClient,
}: {
  children: React.ReactNode
  initialEntries?: string[]
  queryClient?: QueryClient
}) {
  const client = queryClient ?? createTestQueryClient()

  return (
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={initialEntries}>
        {children}
      </MemoryRouter>
    </QueryClientProvider>
  )
}

/**
 * Custom render that wraps the component with all app-level providers:
 * - QueryClientProvider (React Query)
 * - MemoryRouter (React Router)
 *
 * Re-exports all @testing-library/react utilities so tests only need
 * to import from `@/test/utils`.
 *
 * @example
 * import { render, screen } from '@/test/utils'
 * render(<MyComponent />)
 * expect(screen.getByText('Hello')).toBeInTheDocument()
 */
function customRender(ui: ReactElement, options: CustomRenderOptions = {}) {
  const { initialEntries, queryClient, ...renderOptions } = options

  return render(ui, {
    wrapper: ({ children }) => (
      <AllProviders initialEntries={initialEntries} queryClient={queryClient}>
        {children}
      </AllProviders>
    ),
    ...renderOptions,
  })
}

export * from '@testing-library/react'
export { customRender as render, createTestQueryClient }
