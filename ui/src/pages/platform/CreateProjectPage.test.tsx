import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import CreateProjectPage from './CreateProjectPage'
import type { Region } from '@/types/control-plane'

const listRegionsMock = vi.fn<() => Promise<Region[]>>()
const createProjectMock = vi.fn()
const listRecordsMock = vi.fn()
const navigateMock = vi.fn()

vi.mock('@snackbase/react', () => ({
  useSnackBase: () => ({
    records: { list: listRecordsMock },
    internalAuthManager: { token: 'test-token' },
  }),
  useAuth: () => ({ user: { email: 'owner@example.com' } }),
}))

vi.mock('react-router', async () => {
  const actual = await vi.importActual<typeof import('react-router')>('react-router')
  return { ...actual, useNavigate: () => navigateMock }
})

vi.mock('@/lib/control-plane/regions', () => ({
  listAvailableRegions: () => listRegionsMock(),
  isRegionAvailable: () => true,
}))

vi.mock('@/lib/control-plane/create-project', () => ({
  createProject: (...args: unknown[]) => createProjectMock(...args),
}))

vi.mock('@/lib/control-plane/enqueue-provision', () => ({
  enqueueProvisionJob: vi.fn(async () => ({})),
}))

/**
 * @param sortOrder mirrors the codelist `sort_order` the Console sorts by
 */
function region(code: string, name: string, country: string, sortOrder: number): Region {
  return { id: code, code, name, country, status: 'available', sort_order: sortOrder }
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <CreateProjectPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('CreateProjectPage region selection', () => {
  beforeEach(() => {
    listRegionsMock.mockReset()
    createProjectMock.mockReset()
    listRecordsMock.mockReset()
    navigateMock.mockReset()
    listRecordsMock.mockResolvedValue({
      items: [{ id: 'org-1', name: 'Acme', slug: 'acme', status: 'active' }],
    })
  })

  it('auto-selects the sole available region', async () => {
    listRegionsMock.mockResolvedValue([region('eu-01', 'EU Central (Germany)', 'DE', 1)])
    renderPage()
    await waitFor(() => {
      expect(screen.getByTestId('project-region-select')).toHaveTextContent(
        'EU Central (Germany)',
      )
    })
  })

  it('pre-selects nothing when two regions are available', async () => {
    listRegionsMock.mockResolvedValue([
      region('eu-01', 'EU Central (Germany)', 'DE', 1),
      region('eu-02', 'EU West (Amsterdam)', 'NL', 2),
    ])
    renderPage()
    await waitFor(() => {
      expect(screen.getByTestId('project-region-select')).toHaveTextContent(
        /select region/i,
      )
    })
    expect(screen.getByTestId('project-region-select')).not.toHaveTextContent(
      'EU Central (Germany)',
    )
  })

  it('requires an explicit region before submitting with two regions', async () => {
    const user = userEvent.setup()
    listRegionsMock.mockResolvedValue([
      region('eu-01', 'EU Central (Germany)', 'DE', 1),
      region('eu-02', 'EU West (Amsterdam)', 'NL', 2),
    ])
    renderPage()
    await waitFor(() => {
      expect(screen.getByTestId('project-region-select')).toBeEnabled()
    })

    await user.type(screen.getByLabelText(/^name$/i), 'Acme API')
    await user.click(screen.getByTestId('create-project-submit'))

    await waitFor(() => {
      expect(screen.getByText(/region is required/i)).toBeInTheDocument()
    })
    expect(createProjectMock).not.toHaveBeenCalled()
  })

  it('offers regions by location only, with no infrastructure hint', async () => {
    listRegionsMock.mockResolvedValue([
      region('eu-01', 'EU Central (Germany)', 'DE', 1),
      region('eu-02', 'EU West (Amsterdam)', 'NL', 2),
    ])
    const { container } = renderPage()
    await waitFor(() => {
      expect(screen.getByTestId('project-region-select')).toBeEnabled()
    })
    const markup = container.innerHTML.toLowerCase()
    for (const vendor of ['railway', 'momo', 'provider']) {
      expect(markup).not.toContain(vendor)
    }
  })
})
