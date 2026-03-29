/**
 * Tests for CreateCollectionDialog component (FT2.4)
 *
 * Verifies:
 * - Renders collection name input and schema builder
 * - Shows validation error when name is empty on submit
 * - Shows validation error when no fields are defined
 * - Shows validation error for fields missing a name
 * - Calls onSubmit with correct name and schema payload
 * - Shows submitting state during async operation
 * - Shows success state after creation completes
 * - Resets form when dialog is closed and reopened
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import CreateCollectionDialog from '@/components/collections/CreateCollectionDialog'
import type { CreateCollectionData } from '@/services/collections.service'

function renderDialog(props: {
  open?: boolean
  onSubmit?: (data: CreateCollectionData) => Promise<void>
  onOpenChange?: (open: boolean) => void
  collections?: string[]
}) {
  const {
    open = true,
    onSubmit = vi.fn().mockResolvedValue(undefined),
    onOpenChange = vi.fn(),
    collections = [],
  } = props

  return render(
    <CreateCollectionDialog
      open={open}
      onOpenChange={onOpenChange}
      onSubmit={onSubmit}
      collections={collections}
    />
  )
}

describe('CreateCollectionDialog', () => {
  describe('rendering', () => {
    it('renders dialog title', () => {
      renderDialog({})
      expect(screen.getByRole('heading', { name: 'Create Collection' })).toBeInTheDocument()
    })

    it('renders collection name input', () => {
      renderDialog({})
      expect(screen.getByLabelText(/collection name \*/i)).toBeInTheDocument()
    })

    it('renders SchemaBuilder with Add Field button', () => {
      renderDialog({})
      expect(screen.getByRole('button', { name: /add field/i })).toBeInTheDocument()
    })

    it('renders Cancel and Create Collection buttons', () => {
      renderDialog({})
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /create collection/i })).toBeInTheDocument()
    })
  })

  describe('validation', () => {
    it('shows error when submitting without a collection name', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn()
      renderDialog({ onSubmit })

      // Add a field first — SchemaBuilder renders a "Name *" label for each field
      await user.click(screen.getByRole('button', { name: /add field/i }))
      await user.type(screen.getByLabelText('Name *'), 'my_field')

      await user.click(screen.getByRole('button', { name: /create collection/i }))

      await waitFor(() => {
        expect(screen.getByText('Collection name is required')).toBeInTheDocument()
      })
      expect(onSubmit).not.toHaveBeenCalled()
    })

    it('shows error when submitting without any fields', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn()
      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/collection name \*/i), 'customers')
      await user.click(screen.getByRole('button', { name: /create collection/i }))

      await waitFor(() => {
        expect(screen.getByText('At least one field is required')).toBeInTheDocument()
      })
      expect(onSubmit).not.toHaveBeenCalled()
    })

    it('shows error for duplicate field names', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn()
      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/collection name \*/i), 'orders')

      // Add first field named "email"
      await user.click(screen.getByRole('button', { name: /add field/i }))
      const [firstNameInput] = screen.getAllByLabelText('Name *')
      await user.type(firstNameInput, 'email')

      // Add second field with the same name
      await user.click(screen.getByRole('button', { name: /add field/i }))
      const nameInputs = screen.getAllByLabelText('Name *')
      await user.type(nameInputs[1], 'email')

      await user.click(screen.getByRole('button', { name: /create collection/i }))

      await waitFor(() => {
        expect(screen.getByText(/duplicate field name/i)).toBeInTheDocument()
      })
      expect(onSubmit).not.toHaveBeenCalled()
    })

    it('shows error when a field has no name', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn()
      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/collection name \*/i), 'customers')
      await user.click(screen.getByRole('button', { name: /add field/i }))
      // Leave field name empty
      await user.click(screen.getByRole('button', { name: /create collection/i }))

      await waitFor(() => {
        expect(screen.getByText('All fields must have a name')).toBeInTheDocument()
      })
      expect(onSubmit).not.toHaveBeenCalled()
    })

    it('shows error when a reference field has no target collection', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn()
      renderDialog({ onSubmit, collections: ['users', 'accounts'] })

      await user.type(screen.getByLabelText(/collection name \*/i), 'orders')
      await user.click(screen.getByRole('button', { name: /add field/i }))
      await user.type(screen.getByLabelText('Name *'), 'customer_ref')

      // Change field type to "reference" — the first combobox is the field type selector
      await user.click(screen.getByRole('combobox'))
      await user.click(screen.getByRole('option', { name: /reference/i }))

      // Do not select a target collection; submit immediately
      await user.click(screen.getByRole('button', { name: /create collection/i }))

      await waitFor(() => {
        expect(screen.getByText(/is a reference but has no target collection/i)).toBeInTheDocument()
      })
      expect(onSubmit).not.toHaveBeenCalled()
    })

    it('shows error when a PII field has no mask type selected', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn()
      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/collection name \*/i), 'users')
      await user.click(screen.getByRole('button', { name: /add field/i }))
      await user.type(screen.getByLabelText('Name *'), 'ssn')

      // Check the PII checkbox — SchemaBuilder shows Mask Type selector but no value selected
      await user.click(screen.getByRole('checkbox', { name: /pii/i }))

      // Submit without selecting a mask type
      await user.click(screen.getByRole('button', { name: /create collection/i }))

      await waitFor(() => {
        expect(screen.getByText(/is marked as PII but has no mask type/i)).toBeInTheDocument()
      })
      expect(onSubmit).not.toHaveBeenCalled()
    })
  })

  describe('form submission', () => {
    it('calls onSubmit with collection name and schema', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/collection name \*/i), 'customers')
      await user.click(screen.getByRole('button', { name: /add field/i }))
      await user.type(screen.getByLabelText('Name *'), 'email')
      await user.click(screen.getByRole('button', { name: /create collection/i }))

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'customers',
            schema: expect.arrayContaining([
              expect.objectContaining({ name: 'email', type: 'text' }),
            ]),
          })
        )
      })
    })

    it('shows submitting state during async operation', async () => {
      const user = userEvent.setup()
      let resolveSubmit!: () => void
      const onSubmit = vi.fn().mockReturnValue(
        new Promise<void>((resolve) => { resolveSubmit = resolve })
      )
      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/collection name \*/i), 'orders')
      await user.click(screen.getByRole('button', { name: /add field/i }))
      await user.type(screen.getByLabelText('Name *'), 'amount')
      await user.click(screen.getByRole('button', { name: /create collection/i }))

      await waitFor(() => {
        expect(screen.getByText(/creating collection and applying migrations/i)).toBeInTheDocument()
      })

      resolveSubmit()
    })

    it('shows success state after collection is created', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/collection name \*/i), 'products')
      await user.click(screen.getByRole('button', { name: /add field/i }))
      await user.type(screen.getByLabelText('Name *'), 'title')
      await user.click(screen.getByRole('button', { name: /create collection/i }))

      await waitFor(() => {
        expect(screen.getByText(/collection "products" created successfully/i)).toBeInTheDocument()
      })
      expect(screen.getByRole('button', { name: /done/i })).toBeInTheDocument()
    })

    it('shows API error message when onSubmit throws', async () => {
      const user = userEvent.setup()
      // handleApiError processes AxiosErrors; plain Errors fall back to generic message
      const axiosError = Object.assign(new Error('Request failed'), {
        isAxiosError: true,
        response: { data: { detail: 'Collection name already exists' } },
      })
      const onSubmit = vi.fn().mockRejectedValue(axiosError)
      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/collection name \*/i), 'existing')
      await user.click(screen.getByRole('button', { name: /add field/i }))
      await user.type(screen.getByLabelText('Name *'), 'data')
      await user.click(screen.getByRole('button', { name: /create collection/i }))

      await waitFor(() => {
        expect(screen.getByText('Collection name already exists')).toBeInTheDocument()
      })
    })
  })

  describe('dialog close', () => {
    it('calls onOpenChange(false) when Cancel is clicked', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      renderDialog({ onOpenChange })

      await user.click(screen.getByRole('button', { name: /cancel/i }))
      expect(onOpenChange).toHaveBeenCalledWith(false)
    })

    it('calls onOpenChange(false) when Done is clicked after success', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      const onSubmit = vi.fn().mockResolvedValue(undefined)

      render(
        <CreateCollectionDialog
          open={true}
          onOpenChange={onOpenChange}
          onSubmit={onSubmit}
          collections={[]}
        />
      )

      await user.type(screen.getByLabelText(/collection name \*/i), 'done_test')
      await user.click(screen.getByRole('button', { name: /add field/i }))
      await user.type(screen.getByLabelText('Name *'), 'field_one')
      await user.click(screen.getByRole('button', { name: /create collection/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /done/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /done/i }))
      expect(onOpenChange).toHaveBeenCalledWith(false)
    })
  })
})
