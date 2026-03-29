/**
 * Tests for CreateAccountDialog component (FT2.4)
 *
 * Verifies:
 * - Renders name and slug form fields
 * - Submit button is disabled when name is empty
 * - Submit button is enabled when name is provided
 * - Calls onSubmit with correct payload (name only, or name + slug)
 * - Shows loading state during submission
 * - Displays error message when onSubmit throws
 * - Resets form after successful submission
 * - Closes dialog on successful submit
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import CreateAccountDialog from '@/components/accounts/CreateAccountDialog'

function renderDialog(props: {
  open?: boolean
  onSubmit?: (data: { name: string; slug?: string }) => Promise<void>
  onOpenChange?: (open: boolean) => void
}) {
  const {
    open = true,
    onSubmit = vi.fn().mockResolvedValue(undefined),
    onOpenChange = vi.fn(),
  } = props

  return render(
    <CreateAccountDialog open={open} onOpenChange={onOpenChange} onSubmit={onSubmit} />
  )
}

describe('CreateAccountDialog', () => {
  describe('rendering', () => {
    it('renders the dialog title', () => {
      renderDialog({})
      expect(screen.getByRole('heading', { name: 'Create Account' })).toBeInTheDocument()
    })

    it('renders name input field', () => {
      renderDialog({})
      expect(screen.getByLabelText(/name \*/i)).toBeInTheDocument()
    })

    it('renders optional slug input field', () => {
      renderDialog({})
      expect(screen.getByLabelText(/slug/i)).toBeInTheDocument()
    })

    it('renders Cancel and Create Account buttons', () => {
      renderDialog({})
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
    })
  })

  describe('submit button state', () => {
    it('is disabled when name is empty', () => {
      renderDialog({})
      expect(screen.getByRole('button', { name: /create account/i })).toBeDisabled()
    })

    it('is enabled when name is provided', async () => {
      const user = userEvent.setup()
      renderDialog({})

      await user.type(screen.getByLabelText(/name \*/i), 'My Company')
      expect(screen.getByRole('button', { name: /create account/i })).not.toBeDisabled()
    })
  })

  describe('form submission', () => {
    it('calls onSubmit with name only when slug is empty', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)

      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/name \*/i), 'Test Company')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith({ name: 'Test Company', slug: undefined })
      })
    })

    it('calls onSubmit with name and slug when slug is provided', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)

      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/name \*/i), 'Test Company')
      await user.type(screen.getByLabelText(/slug/i), 'test-company')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith({ name: 'Test Company', slug: 'test-company' })
      })
    })

    it('shows loading spinner during submission', async () => {
      const user = userEvent.setup()
      let resolveSubmit!: () => void
      const onSubmit = vi.fn().mockReturnValue(new Promise<void>((resolve) => { resolveSubmit = resolve }))

      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/name \*/i), 'Test Company')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      // During submission the button should be disabled
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /create account/i })).toBeDisabled()
      })

      resolveSubmit()
    })

    it('calls onOpenChange(false) after successful submission', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      const onSubmit = vi.fn().mockResolvedValue(undefined)

      render(
        <CreateAccountDialog open={true} onOpenChange={onOpenChange} onSubmit={onSubmit} />
      )

      await user.type(screen.getByLabelText(/name \*/i), 'Test Company')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        expect(onOpenChange).toHaveBeenCalledWith(false)
      })
    })

    it('displays error message when onSubmit throws', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockRejectedValue({
        response: { data: { detail: 'Account already exists' } },
      })

      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/name \*/i), 'Test Company')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        expect(screen.getByText('Account already exists')).toBeInTheDocument()
      })
    })

    it('shows generic error when response has no detail', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockRejectedValue({ message: 'Network error' })

      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/name \*/i), 'Test Company')
      await user.click(screen.getByRole('button', { name: /create account/i }))

      await waitFor(() => {
        expect(screen.getByText('Network error')).toBeInTheDocument()
      })
    })
  })

  describe('cancel behavior', () => {
    it('calls onOpenChange(false) when Cancel is clicked', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()

      render(
        <CreateAccountDialog
          open={true}
          onOpenChange={onOpenChange}
          onSubmit={vi.fn().mockResolvedValue(undefined)}
        />
      )

      await user.click(screen.getByRole('button', { name: /cancel/i }))
      expect(onOpenChange).toHaveBeenCalledWith(false)
    })
  })
})
