import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import EnvironmentsPage from './EnvironmentsPage'

const getMock = vi.fn()
const listMock = vi.fn()
const patchMock = vi.fn()
const createMock = vi.fn()

vi.mock('@snackbase/react', () => ({
  useSnackBase: () => ({
    records: {
      get: getMock,
      list: listMock,
      patch: patchMock,
      create: createMock,
    },
    internalAuthManager: { token: 'test-token' },
  }),
  useAuth: () => ({
    user: { email: 'admin@example.com' },
    isAuthenticated: true,
    isLoading: false,
  }),
}))

function renderAt(path: string) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route
            path="/organizations/:orgId/projects/:projectId/environments"
            element={<EnvironmentsPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('EnvironmentsPage', () => {
  beforeEach(() => {
    getMock.mockReset()
    listMock.mockReset()
    patchMock.mockReset()
    createMock.mockReset()
    getMock.mockImplementation(async (collection: string) => {
      if (collection === 'projects') {
        return {
          id: 'p1',
          name: 'API',
          slug: 'api',
          region: 'eu-01',
          tenancy_mode: 'single',
          status: 'active',
        }
      }
      if (collection === 'organizations') {
        return { id: 'o1', name: 'Acme', slug: 'acme', status: 'active' }
      }
      return null
    })
  })

  it('shows breadcrumb and project header', async () => {
    listMock.mockResolvedValue({ items: [] })
    renderAt('/organizations/o1/projects/p1/environments')

    await waitFor(() => {
      expect(screen.getByTestId('project-breadcrumb')).toBeInTheDocument()
    })
    expect(screen.getByTestId('project-header')).toHaveTextContent('API')
    expect(screen.getByTestId('project-region-badge')).toHaveTextContent('eu-01')
  })

  it('shows Open Studio and Copy for ready single-tenant environments', async () => {
    listMock.mockResolvedValue({
      items: [
        {
          id: 'e1',
          project: 'p1',
          name: 'Production',
          slug: 'production',
          status: 'ready',
          tenancy_mode: 'single',
          instance_url: 'https://api.example.local',
        },
      ],
    })
    renderAt('/organizations/o1/projects/p1/environments')

    await waitFor(() => {
      expect(screen.getByTestId('open-studio-e1')).toBeInTheDocument()
    })
    expect(screen.getByTestId('copy-url-e1')).toBeInTheDocument()
    expect(screen.getByTestId('open-studio-e1')).toHaveAttribute(
      'href',
      '/project/production/collections',
    )
  })

  it('shows error message for failed environments', async () => {
    listMock.mockResolvedValue({
      items: [
        {
          id: 'e2',
          project: 'p1',
          name: 'Production',
          slug: 'production',
          status: 'failed',
          error_message: 'Host agent timeout',
        },
      ],
    })
    renderAt('/organizations/o1/projects/p1/environments')

    await waitFor(() => {
      expect(screen.getByText('Host agent timeout')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('open-studio-e2')).not.toBeInTheDocument()
    expect(screen.getByTestId('retry-provision-e2')).toBeInTheDocument()
  })

  it('hides deleted environments from the list', async () => {
    listMock.mockResolvedValue({
      items: [
        {
          id: 'e-del',
          project: 'p1',
          name: 'Gone',
          slug: 'gone',
          status: 'deleted',
        },
        {
          id: 'e-live',
          project: 'p1',
          name: 'Production',
          slug: 'production',
          status: 'pending',
        },
      ],
    })
    renderAt('/organizations/o1/projects/p1/environments')

    await waitFor(() => {
      expect(screen.getByTestId('env-row-e-live')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('env-row-e-del')).not.toBeInTheDocument()
  })

  it('shows delete control for non-in-flight environments', async () => {
    listMock.mockResolvedValue({
      items: [
        {
          id: 'e3',
          project: 'p1',
          name: 'Production',
          slug: 'production',
          status: 'ready',
          instance_url: 'http://x.local',
        },
      ],
    })
    renderAt('/organizations/o1/projects/p1/environments')

    await waitFor(() => {
      expect(screen.getByTestId('delete-env-e3')).toBeInTheDocument()
    })
  })
})
