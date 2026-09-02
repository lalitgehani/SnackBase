/**
 * Tests for the restore confirmation dialog (F6.3).
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import { RestoreDialog } from '../RestoreDialog'
import { backupsApi, type BackupEntry } from '@/services/backups'

vi.mock('@/services/backups', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/services/backups')>()
  return {
    ...original,
    backupsApi: {
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

const mockedApi = vi.mocked(backupsApi, true)

function makeEntry(name = 'my_backup.zip'): BackupEntry {
  return {
    name,
    size: 2048,
    modified: '2026-09-02T02:00:00+00:00',
    is_automatic: false,
    backup_type: 'sqlite_physical',
    restorable: true,
  }
}

function renderDialog(entry: BackupEntry | null = makeEntry()) {
  return render(
    <RestoreDialog entry={entry} open onOpenChange={() => undefined} />,
  )
}

describe('RestoreDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedApi.restorePreview.mockResolvedValue({
      archive_name: 'my_backup.zip',
      manifest: {},
      created_at: '2026-09-02T02:00:00+00:00',
      source_version: '0.11.0',
      includes_files: true,
      database_engine: 'sqlite',
      backup_type: 'sqlite_physical',
      blocking: [],
      warnings: [],
    })
  })

  it('keeps confirm disabled until the typed name matches exactly', async () => {
    const user = userEvent.setup()
    renderDialog()

    const confirm = await screen.findByRole('button', { name: 'Restore' })
    expect(confirm).toBeDisabled()

    const input = screen.getByLabelText(/Type the archive name/i)
    await user.type(input, 'my_backup')
    expect(confirm).toBeDisabled()

    await user.type(input, '.zip')
    expect((input as HTMLInputElement).value).toBe('my_backup.zip')
    expect(confirm).toBeEnabled()
  })

  it('disables confirm permanently for blocking issues', async () => {
    mockedApi.restorePreview.mockResolvedValue({
      archive_name: 'my_backup.zip',
      manifest: {},
      created_at: '2026-09-02T02:00:00+00:00',
      source_version: '0.11.0',
      includes_files: false,
      database_engine: 'sqlite',
      backup_type: 'logical',
      blocking: [
        {
          type: 'encryption_key_mismatch',
          severity: 'blocking',
          message: 'Archive was taken with a different key.',
        },
      ],
      warnings: [],
    })
    const user = userEvent.setup()
    renderDialog()

    await screen.findByText(/Blocking issue/i)
    const input = screen.getByLabelText(/Type the archive name/i)
    await user.type(input, 'my_backup.zip')

    expect(screen.getByRole('button', { name: 'Restore' })).toBeDisabled()
    expect(screen.queryByLabelText(/Restore anyway/i)).not.toBeInTheDocument()
  })

  it('adds force: true when the restore-anyway checkbox is checked', async () => {
    mockedApi.restorePreview.mockResolvedValue({
      archive_name: 'my_backup.zip',
      manifest: {},
      created_at: '2026-09-02T02:00:00+00:00',
      source_version: '0.11.0',
      includes_files: false,
      database_engine: 'sqlite',
      backup_type: 'sqlite_physical',
      blocking: [],
      warnings: [
        {
          type: 'token_secret_mismatch',
          severity: 'warning',
          message: 'Tokens will be invalidated.',
        },
      ],
    })
    const user = userEvent.setup()
    mockedApi.restore.mockResolvedValue({ archive_name: 'my_backup.zip' })
    renderDialog()

    const checkbox = await screen.findByLabelText(/Restore anyway/i)
    await user.click(checkbox)

    const input = screen.getByLabelText(/Type the archive name/i)
    await user.type(input, 'my_backup.zip')
    await user.click(screen.getByRole('button', { name: 'Restore' }))

    await waitFor(() => {
      expect(mockedApi.restore).toHaveBeenCalledWith('my_backup.zip', true)
    })
  })

  it('states that data after the archive timestamp is discarded', async () => {
    renderDialog()

    await screen.findByRole('button', { name: 'Restore' })
    expect(screen.getByText(/will be discarded/i)).toBeInTheDocument()
    expect(screen.getByText(/restart/i)).toBeInTheDocument()
  })
})
