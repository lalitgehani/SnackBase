import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router'
import { render } from '@/test/utils'
import CodelistsPage from '../CodelistsPage'
import * as codelistsService from '@/services/codelists.service'
import { useAuthStore } from '@/stores/auth.store'

function renderCodelists(path = '/admin/codelists') {
  return render(
    <Routes>
      <Route path="/admin/codelists" element={<CodelistsPage />} />
      <Route path="/admin/codelists/:code" element={<CodelistsPage />} />
    </Routes>,
    { initialEntries: [path] },
  )
}

vi.mock('@/services/codelists.service', async () => {
  const actual = await vi.importActual<typeof import('@/services/codelists.service')>(
    '@/services/codelists.service',
  )
  return {
    ...actual,
    listCodelists: vi.fn(),
    listManageValues: vi.fn(),
    getEffectiveValues: vi.fn(),
    listOverrides: vi.fn(),
    createCodelist: vi.fn(),
    setOverride: vi.fn(),
    clearOverride: vi.fn(),
  }
})

describe('CodelistsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({
      user: {
        id: 'u1',
        email: 'admin@test.com',
        role: 'admin',
        account_id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
      } as never,
      account: {
        id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        slug: 'acct-a',
        name: 'Account A',
      } as never,
      token: 't',
      isAuthenticated: true,
    })
    vi.mocked(codelistsService.listCodelists).mockResolvedValue([
      {
        id: '1',
        code: 'regions',
        name: 'Cloud Regions',
        scope: 'system',
        account_id: '00000000-0000-0000-0000-000000000000',
        is_system: true,
        is_extensible: false,
        is_active: true,
        is_builtin: true,
      },
    ])
    vi.mocked(codelistsService.listManageValues).mockResolvedValue([
      {
        id: 'v1',
        codelist_id: '1',
        code: 'eu-01',
        sort_order: 1,
        is_active: true,
        scope: 'system',
        account_id: '00000000-0000-0000-0000-000000000000',
        is_system: true,
        labels: [{ language: 'en', label: 'EU Central (Germany)' }],
      },
    ])
    vi.mocked(codelistsService.getEffectiveValues).mockResolvedValue([
      {
        code: 'eu-01',
        label: 'EU Central (Germany)',
        is_default: false,
        sort_order: 1,
        scope: 'system',
        is_active: true,
        value_id: 'v1',
      },
    ])
    vi.mocked(codelistsService.listOverrides).mockResolvedValue([])
  })

  it('renders workspace shell and empty detail', async () => {
    renderCodelists('/admin/codelists')
    expect(await screen.findByTestId('codelists-workspace')).toBeInTheDocument()
    expect(screen.getByTestId('codelist-empty-detail')).toBeInTheDocument()
    expect(screen.getAllByText(/System/).length).toBeGreaterThan(0)
  })

  it('loads rail and opens detail values tab', async () => {
    const user = userEvent.setup()
    renderCodelists('/admin/codelists')
    const railItem = await screen.findByTestId('codelist-rail-regions')
    await user.click(railItem)
    await waitFor(() => {
      expect(screen.getByTestId('values-table')).toBeInTheDocument()
    })
    expect(screen.getByText('eu-01')).toBeInTheDocument()
    expect(screen.getByText('EU Central (Germany)')).toBeInTheDocument()
  })

  it('shows create dialog code validation error', async () => {
    const user = userEvent.setup()
    renderCodelists('/admin/codelists')
    await screen.findByTestId('codelist-create-btn')
    await user.click(screen.getByTestId('codelist-create-btn'))
    const input = await screen.findByTestId('create-code-input')
    await user.type(input, 'Bad-Code')
    await user.type(screen.getByLabelText(/^Name$/i), 'Bad')
    await user.click(screen.getByRole('button', { name: /^Create$/i }))
    expect(await screen.findByTestId('create-code-error')).toBeInTheDocument()
  })

  it('shows overrides callout on overrides tab', async () => {
    const user = userEvent.setup()
    renderCodelists('/admin/codelists/regions')
    await waitFor(() => expect(codelistsService.listManageValues).toHaveBeenCalled())
    await user.click(screen.getByRole('tab', { name: /Overrides/i }))
    expect(await screen.findByTestId('overrides-callout')).toBeInTheDocument()
    expect(screen.getByTestId('effective-preview')).toBeInTheDocument()
  })
})
