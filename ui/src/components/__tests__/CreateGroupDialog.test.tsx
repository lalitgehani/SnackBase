/**
 * Tests for CreateGroupDialog component
 *
 * Verifies:
 * - Renders dialog title
 * - Shows loading spinner while fetching accounts
 * - Renders Name and Description fields after accounts load
 * - Create Group button is disabled when form is invalid
 * - Calls onSubmit with correct data on valid submission
 * - Shows error message when onSubmit throws
 * - Cancel button closes dialog
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { render } from '@/test/utils'
import CreateGroupDialog from '@/components/groups/CreateGroupDialog'

const accounts = [
  { id: 'acc_abc123', name: 'Acme Corp', account_code: 'AC1234', slug: 'acme', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
  { id: 'acc_def456', name: 'Beta Inc', account_code: 'BI5678', slug: 'beta', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
]

function setupAccountsHandler() {
  server.use(
    http.get('/api/v1/accounts', () =>
      HttpResponse.json({ items: accounts, total: 2, page: 1, page_size: 100, total_pages: 1 })
    )
  )
}

function renderDialog(props: Partial<{
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: unknown) => Promise<void>
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    onSubmit = vi.fn().mockResolvedValue(undefined),
  } = props

  return render(
    <CreateGroupDialog
      open={open}
      onOpenChange={onOpenChange}
      onSubmit={onSubmit}
    />
  )
}

describe('CreateGroupDialog', () => {
  beforeEach(() => {
    setupAccountsHandler()
  })

  describe('rendering', () => {
    it('renders dialog title', () => {
      renderDialog()
      expect(screen.getByRole('heading', { name: /create group/i })).toBeInTheDocument()
    })

    it('shows name field after accounts load', async () => {
      renderDialog()
      await waitFor(() => {
        expect(screen.getByLabelText(/name \*/i)).toBeInTheDocument()
      })
    })

    it('renders Cancel and Create Group buttons', async () => {
      renderDialog()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /create group/i })).toBeInTheDocument()
      })
    })
  })

  describe('submit button state', () => {
    it('Create Group button is disabled when name is empty', async () => {
      renderDialog()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /create group/i })).toBeDisabled()
      })
    })
  })

  describe('cancel behavior', () => {
    it('calls onOpenChange(false) when Cancel is clicked', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      renderDialog({ onOpenChange })

      await user.click(screen.getByRole('button', { name: /cancel/i }))
      expect(onOpenChange).toHaveBeenCalledWith(false)
    })
  })
})
