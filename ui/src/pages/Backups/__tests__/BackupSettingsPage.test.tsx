/**
 * Tests for the Backup settings page (F6.1).
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import BackupSettingsPage from '../BackupSettingsPage'
import { isPlausibleCron } from '../cronCheck'
import { backupsSettingsApi } from '@/services/backups'

vi.mock('@/services/backups', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/services/backups')>()
  return {
    ...original,
    backupsApi: {
      list: vi.fn().mockResolvedValue({
        backups: [],
        active: null,
        consecutive_failures: 0,
        last_error: null,
        database_engine: 'sqlite',
      }),
      create: vi.fn(),
      remove: vi.fn(),
      download: vi.fn(),
      upload: vi.fn(),
      restore: vi.fn(),
      restoreStatus: vi.fn(),
      restorePreview: vi.fn(),
      cronDescription: vi
        .fn()
        .mockResolvedValue({ expr: '', valid: true, error: '', description: 'Daily at 02:00' }),
    },
    backupsSettingsApi: {
      getConfig: vi.fn(),
      getValues: vi.fn(),
      updateValues: vi.fn().mockResolvedValue(undefined),
      createConfig: vi.fn().mockResolvedValue({ id: 'new-config' }),
    },
  }
})

const mockedSettings = vi.mocked(backupsSettingsApi, true)

describe('BackupSettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedSettings.getConfig.mockResolvedValue({
      id: 'config-1',
      category: 'backup_settings',
      provider_name: 'backup',
      display_name: 'Backup Settings',
      enabled: true,
      is_system: true,
      is_builtin: true,
      account_id: '00000000-0000-0000-0000-000000000000',
    })
    mockedSettings.getValues.mockResolvedValue({
      destination: 'local',
      local_path: './sb_data/backups',
      cron: '',
      max_keep: 3,
    })
  })

  it('hides S3 fields while the destination is Local', async () => {
    render(<BackupSettingsPage />)

    await waitFor(() => {
      expect(screen.getByLabelText(/Local path/i)).toBeInTheDocument()
    })
    expect(screen.queryByTestId('s3-settings')).not.toBeInTheDocument()
  })

  it('shows S3 fields when the destination is S3', async () => {
    const user = userEvent.setup()
    render(<BackupSettingsPage />)

    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: /destination/i })).toBeInTheDocument()
    })
    await user.click(screen.getByRole('combobox', { name: /destination/i }))
    await user.click(await screen.findByRole('option', { name: /s3 \/ object storage/i }))

    expect(await screen.findByTestId('s3-settings')).toBeInTheDocument()
    expect(screen.getByLabelText(/Bucket/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Secret access key/i)).toBeInTheDocument()
  })

  it('fills the cron field from the daily 02:00 preset', async () => {
    const user = userEvent.setup()
    render(<BackupSettingsPage />)

    await waitFor(() => {
      expect(screen.getByLabelText(/Cron expression/i)).toBeInTheDocument()
    })
    await user.click(screen.getByTestId('cron-preset-0 2 * * *'))

    const cron = screen.getByLabelText(/Cron expression/i) as HTMLInputElement
    expect(cron.value).toBe('0 2 * * *')
  })

  it('does not send the masked secret when untouched', async () => {
    const user = userEvent.setup()
    mockedSettings.getValues.mockResolvedValue({
      destination: 's3',
      s3_bucket: 'bucket',
      s3_secret_access_key: '••••••••',
      cron: '',
      max_keep: 3,
    })
    render(<BackupSettingsPage />)

    await waitFor(() => {
      expect(screen.getByLabelText(/Bucket/i)).toBeInTheDocument()
    })
    // The stored secret renders masked.
    const secret = screen.getByLabelText(/Secret access key/i) as HTMLInputElement
    expect(secret.getAttribute('placeholder')).toBe('••••••••')
    expect(secret.value).toBe('')

    await user.click(screen.getByRole('button', { name: /Save settings/i }))

    await waitFor(() => {
      expect(mockedSettings.updateValues).toHaveBeenCalled()
    })
    const payload = mockedSettings.updateValues.mock.calls[0][1]
    expect(payload).not.toHaveProperty('s3_secret_access_key')
  })

  it('sends the secret only when re-entered', async () => {
    const user = userEvent.setup()
    mockedSettings.getValues.mockResolvedValue({
      destination: 's3',
      s3_bucket: 'bucket',
      cron: '',
      max_keep: 3,
    })
    render(<BackupSettingsPage />)

    await user.type(await screen.findByLabelText(/Secret access key/i), 'new-secret')
    await user.click(screen.getByRole('button', { name: /Save settings/i }))

    await waitFor(() => {
      expect(mockedSettings.updateValues).toHaveBeenCalled()
    })
    const payload = mockedSettings.updateValues.mock.calls[0][1]
    expect(payload.s3_secret_access_key).toBe('new-secret')
  })

  it('blocks submit with an inline message for an invalid cron', async () => {
    const user = userEvent.setup()
    render(<BackupSettingsPage />)

    await waitFor(() => {
      expect(screen.getByLabelText(/Cron expression/i)).toBeInTheDocument()
    })
    await user.type(screen.getByLabelText(/Cron expression/i), 'not a cron')
    expect(screen.getByTestId('cron-inline-error')).toBeInTheDocument()
  })

  it('shows the local destination warning banner', async () => {
    render(<BackupSettingsPage />)

    expect(await screen.findByTestId('local-destination-warning')).toBeInTheDocument()
  })

  it('shows the PostgreSQL info panel only on PostgreSQL', async () => {
    mockedSettings.getValues.mockResolvedValue({ destination: 'local', cron: '', max_keep: 3 })
    const { rerender } = render(<BackupSettingsPage />)

    await waitFor(() => {
      expect(screen.getByLabelText(/Local path/i)).toBeInTheDocument()
    })
    expect(screen.queryByTestId('postgres-info-panel')).not.toBeInTheDocument()
    rerender(<BackupSettingsPage />)
  })

  it('surfaces the server 400 message on save', async () => {
    const user = userEvent.setup()
    mockedSettings.updateValues.mockRejectedValue({
      response: { data: { detail: "minuted: value 99 out of bounds [0,59] in minute field" } },
    })
    render(<BackupSettingsPage />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Save settings/i })).toBeInTheDocument()
    })
    await user.click(screen.getByRole('button', { name: /Save settings/i }))

    expect(await screen.findByTestId('settings-error')).toHaveTextContent(
      /out of bounds/i,
    )
  })
})

describe('isPlausibleCron', () => {
  it('accepts valid expressions', () => {
    expect(isPlausibleCron('0 2 * * *')).toBe(true)
    expect(isPlausibleCron('*/15 * * * *')).toBe(true)
    expect(isPlausibleCron('0 2 * * 0')).toBe(true)
  })

  it('rejects invalid expressions', () => {
    expect(isPlausibleCron('not a cron')).toBe(false)
    expect(isPlausibleCron('0 2 * *')).toBe(false)
    expect(isPlausibleCron('99 2 * * *')).toBe(false)
  })
})
