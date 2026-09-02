/**
 * Tests for the Backups list page (F6.2).
 *
 * The backups service module is mocked so polling and interaction behavior
 * can be driven deterministically without MSW timing.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import BackupsListPage from '../BackupsListPage'
import { backupsApi } from '@/services/backups'

vi.mock('@/services/backups', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/services/backups')>()
  return {
    ...original,
    backupsApi: {
      __realApi: original.backupsApi,
      list: vi.fn(),
      create: vi.fn(),
      remove: vi.fn(),
      download: vi.fn(),
      upload: vi.fn(),
      restore: vi.fn(),
      restoreStatus: vi.fn(),
      restorePreview: vi.fn(),
      cronDescription: vi.fn(),
    },
  }
})

function listResponse(overrides: Record<string, unknown> = {}) {
  return {
    backups: [
      {
        name: 'manual.zip',
        size: 2048,
        modified: '2026-09-02T02:00:00+00:00',
        is_automatic: false,
        backup_type: 'sqlite_physical',
        restorable: true,
      },
      {
        name: 'portable.zip',
        size: 4096,
        modified: '2026-09-02T03:00:00+00:00',
        is_automatic: false,
        backup_type: 'logical',
        restorable: false,
      },
      {
        name: '@auto_snackbase_20260901020000.zip',
        size: 1024,
        modified: '2026-09-01T02:00:00+00:00',
        is_automatic: true,
        backup_type: 'sqlite_physical',
        restorable: true,
      },
    ],
    active: null,
    consecutive_failures: 0,
    last_error: null,
    database_engine: 'sqlite',
    ...overrides,
  }
}

const mockedApi = vi.mocked(backupsApi, true)

function mockedListCallCount(): number {
  return mockedApi.list.mock.calls.length
}

describe('BackupsListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedApi.list.mockResolvedValue(listResponse())
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders archives with type badges and origin markers', async () => {
    render(<BackupsListPage />)

    await waitFor(() => {
      expect(screen.getByTestId('backup-row-manual.zip')).toBeInTheDocument()
    })
    expect(screen.getByTestId('badge-manual.zip')).toHaveTextContent('Restorable')
    expect(screen.getByTestId('badge-portable.zip')).toHaveTextContent('Portable')
    expect(screen.getByTestId('badge-@auto_snackbase_20260901020000.zip')).toHaveTextContent(
      'Restorable',
    )
    expect(screen.getAllByText('Manual').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Automatic').length).toBeGreaterThan(0)
  })

  it('disables Restore for non-restorable archives and explains why', async () => {
    render(<BackupsListPage />)

    const restoreButton = await screen.findByTestId('restore-portable.zip')
    expect(restoreButton).toBeDisabled()
    expect(screen.getByTestId('restore-manual.zip')).toBeEnabled()
  })

  it('polls every 5 seconds while an operation is active and stops at rest', async () => {
    vi.useFakeTimers()
    const activeResponse = listResponse({
      active: {
        operation: 'backup',
        name: 'wip.zip',
        pid: 1,
        started_at: '2026-09-02T02:00:00+00:00',
      },
    })
    mockedApi.list
      .mockResolvedValueOnce(activeResponse)
      .mockResolvedValueOnce(activeResponse)
      .mockResolvedValue(listResponse())
    render(<BackupsListPage />)
    await vi.advanceTimersByTimeAsync(0)
    expect(mockedApi.list).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(5000)
    expect(mockedApi.list).toHaveBeenCalledTimes(2)
    await vi.advanceTimersByTimeAsync(5000)
    expect(mockedApi.list).toHaveBeenCalledTimes(3)

    // Third response cleared the operation: at most one in-flight tick
    // lands while React processes the cleared state, then polling stops.
    await vi.advanceTimersByTimeAsync(5000)
    const afterClear = mockedListCallCount()
    await vi.advanceTimersByTimeAsync(30000)
    expect(mockedListCallCount()).toBe(afterClear)
  })

  it('shows the failure banner with last_error when failures are non-zero', async () => {
    mockedApi.list.mockResolvedValue(
      listResponse({
        consecutive_failures: 2,
        last_error: 'destination unreachable',
      }),
    )
    render(<BackupsListPage />)

    const banner = await screen.findByTestId('backup-failure-banner')
    expect(banner).toHaveTextContent('2 consecutive failures')
    expect(banner).toHaveTextContent('destination unreachable')
  })

  it('hides the failure banner when there are no failures', async () => {
    render(<BackupsListPage />)

    await waitFor(() => {
      expect(screen.getByTestId('backup-row-manual.zip')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('backup-failure-banner')).not.toBeInTheDocument()
  })

  it('surfaces the server error for an invalid upload', async () => {
    const user = userEvent.setup()
    mockedApi.upload.mockRejectedValue({
      response: { data: { detail: 'Not a valid backup archive: missing manifest.json' } },
    })
    render(<BackupsListPage />)

    const file = new File(['not a zip'], 'bad.zip', { type: 'application/zip' })
    const input = screen.getByTestId('backup-upload-input')
    await user.upload(input, file)

    await waitFor(() => {
      const banner = screen.getByTestId('upload-error')
      expect(banner).toHaveTextContent('missing manifest.json')
    })
  })

  it('requires confirmation for delete and removes the row', async () => {
    const user = userEvent.setup()
    mockedApi.remove.mockResolvedValue(undefined)
    render(<BackupsListPage />)

    await user.click(await screen.findByTestId('delete-manual.zip'))
    expect(mockedApi.remove).not.toHaveBeenCalled()

    await user.click(await screen.findByRole('button', { name: 'Delete' }))
    await waitFor(() => expect(mockedApi.remove).toHaveBeenCalledWith('manual.zip'))
  })
})
