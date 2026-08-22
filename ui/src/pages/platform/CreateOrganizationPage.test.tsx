import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import CreateOrganizationPage from './CreateOrganizationPage'

const createMock = vi.fn()
const navigateMock = vi.fn()

vi.mock('@snackbase/react', () => ({
  useSnackBase: () => ({
    records: { create: createMock },
  }),
}))

vi.mock('react-router', async () => {
  const actual = await vi.importActual<typeof import('react-router')>('react-router')
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <CreateOrganizationPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('CreateOrganizationPage', () => {
  beforeEach(() => {
    createMock.mockReset()
    navigateMock.mockReset()
  })

  it('validates required name', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(screen.getByTestId('create-org-submit'))
    await waitFor(() => {
      expect(screen.getByText(/name is required/i)).toBeInTheDocument()
    })
    expect(createMock).not.toHaveBeenCalled()
  })

  it('auto-derives slug and creates organization', async () => {
    const user = userEvent.setup()
    createMock.mockResolvedValue({
      id: 'org-1',
      name: 'Acme Team',
      slug: 'acme-team',
      status: 'active',
    })
    renderPage()

    await user.type(screen.getByLabelText(/^name$/i), 'Acme Team')
    await waitFor(() => {
      expect(screen.getByLabelText(/^slug$/i)).toHaveValue('acme-team')
    })
    await user.click(screen.getByTestId('create-org-submit'))

    await waitFor(() => {
      expect(createMock).toHaveBeenCalledWith('organizations', {
        name: 'Acme Team',
        slug: 'acme-team',
        status: 'active',
      })
    })
    expect(navigateMock).toHaveBeenCalledWith(
      '/organizations/org-1/projects',
      { replace: true },
    )
  })
})
