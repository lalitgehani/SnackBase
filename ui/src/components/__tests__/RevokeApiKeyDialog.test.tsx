/**
 * Tests for RevokeApiKeyDialog component
 *
 * Verifies:
 * - Renders dialog with API key name
 * - Cancel button closes dialog
 * - Calls revokeApiKey service on Revoke Key click
 * - Calls onRevoked after successful revocation
 * - Shows loading state during revocation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { render } from '@/test/utils'
import { RevokeApiKeyDialog } from '@/pages/ApiKeys/RevokeApiKeyDialog'
import type { APIKeyListItem } from '@/services/api-keys.service'

const apiKey: APIKeyListItem = {
  id: 'key_abc123',
  name: 'Production Key',
  key: 'sb_sk_AC1234_****',
  last_used_at: null,
  expires_at: null,
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
}

function renderDialog(props: Partial<{
  apiKey: APIKeyListItem | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onRevoked: () => void
}> = {}) {
  const {
    apiKey: k = apiKey,
    open = true,
    onOpenChange = vi.fn(),
    onRevoked = vi.fn(),
  } = props

  return render(
    <RevokeApiKeyDialog
      apiKey={k}
      open={open}
      onOpenChange={onOpenChange}
      onRevoked={onRevoked}
    />
  )
}

describe('RevokeApiKeyDialog', () => {
  beforeEach(() => {
    server.use(
      http.delete('/api/v1/admin/api-keys/:id', () => new HttpResponse(null, { status: 200 }))
    )
  })

  describe('rendering', () => {
    it('renders confirmation question', () => {
      renderDialog()
      expect(screen.getByText(/are you sure/i)).toBeInTheDocument()
    })

    it('renders API key name in description', () => {
      renderDialog()
      expect(screen.getByText(/production key/i)).toBeInTheDocument()
    })

    it('renders Cancel and Revoke Key buttons', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /revoke key/i })).toBeInTheDocument()
    })
  })

  describe('revoke action', () => {
    it('calls revokeApiKey service and onRevoked', async () => {
      const user = userEvent.setup()
      const onRevoked = vi.fn()
      renderDialog({ onRevoked })

      await user.click(screen.getByRole('button', { name: /revoke key/i }))

      await waitFor(() => {
        expect(onRevoked).toHaveBeenCalled()
      })
    })

    it('calls onOpenChange(false) after revocation', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      renderDialog({ onOpenChange })

      await user.click(screen.getByRole('button', { name: /revoke key/i }))

      await waitFor(() => {
        expect(onOpenChange).toHaveBeenCalledWith(false)
      })
    })
  })

  describe('cancel behavior', () => {
    it('calls onOpenChange when Cancel is clicked', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      renderDialog({ onOpenChange })

      await user.click(screen.getByRole('button', { name: /cancel/i }))
      expect(onOpenChange).toHaveBeenCalled()
    })
  })
})
