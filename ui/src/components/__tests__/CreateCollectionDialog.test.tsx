/**
 * Tests for CreateCollectionDialog (legacy dialog; primary UX is /collections/new)
 */

import { describe, it, expect, vi } from 'vitest'
import { SnackBaseError } from '@snackbase/sdk'
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
    />,
  )
}

async function addNamedField(
  user: ReturnType<typeof userEvent.setup>,
  name: string,
  fieldIndex = 1,
) {
  await user.click(screen.getByRole('button', { name: /add field/i }))
  await user.type(
    screen.getByLabelText(new RegExp(`field ${fieldIndex} name`, 'i')),
    name,
  )
}

describe('CreateCollectionDialog', () => {
  describe('rendering', () => {
    it('renders dialog title', () => {
      renderDialog({})
      expect(screen.getByRole('heading', { name: 'Create Collection' })).toBeInTheDocument()
    })

    it('renders collection name input and schema table', () => {
      renderDialog({})
      expect(screen.getByLabelText(/collection name \*/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /add field/i })).toBeInTheDocument()
      expect(screen.getByTestId('system-fields-panel')).toBeInTheDocument()
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

      await addNamedField(user, 'my_field')
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
      await addNamedField(user, 'email', 1)
      await addNamedField(user, 'email', 2)

      await user.click(screen.getByRole('button', { name: /create collection/i }))

      await waitFor(() => {
        expect(screen.getAllByText(/duplicate field name/i).length).toBeGreaterThan(0)
      })
      expect(onSubmit).not.toHaveBeenCalled()
    })

    it('shows error when a field has no name', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn()
      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/collection name \*/i), 'customers')
      await user.click(screen.getByRole('button', { name: /add field/i }))
      await user.click(screen.getByRole('button', { name: /create collection/i }))

      await waitFor(() => {
        expect(screen.getAllByText(/field name is required/i).length).toBeGreaterThan(0)
      })
      expect(onSubmit).not.toHaveBeenCalled()
    })

    it('shows error when a reference field has no target collection', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn()
      renderDialog({ onSubmit, collections: ['users', 'accounts'] })

      await user.type(screen.getByLabelText(/collection name \*/i), 'orders')
      await addNamedField(user, 'customer_ref')

      await user.click(screen.getByRole('combobox', { name: /field 1 type/i }))
      await user.click(screen.getByRole('option', { name: /reference/i }))

      await user.click(screen.getByRole('button', { name: /create collection/i }))

      await waitFor(() => {
        expect(screen.getAllByText(/target collection is required/i).length).toBeGreaterThan(0)
      })
      expect(onSubmit).not.toHaveBeenCalled()
    })

    it('shows error when a PII field has no mask type selected', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn()
      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/collection name \*/i), 'users')
      await addNamedField(user, 'ssn')
      await user.click(screen.getByRole('checkbox', { name: /field 1 pii/i }))

      await user.click(screen.getByRole('button', { name: /create collection/i }))

      await waitFor(() => {
        expect(screen.getAllByText(/mask type is required/i).length).toBeGreaterThan(0)
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
      await addNamedField(user, 'email')
      await user.click(screen.getByRole('button', { name: /create collection/i }))

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'customers',
            schema: expect.arrayContaining([
              expect.objectContaining({ name: 'email', type: 'text' }),
            ]),
          }),
        )
      })
    })

    it('shows submitting state during async operation', async () => {
      const user = userEvent.setup()
      let resolveSubmit!: () => void
      const onSubmit = vi.fn().mockReturnValue(
        new Promise<void>((resolve) => {
          resolveSubmit = resolve
        }),
      )
      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/collection name \*/i), 'orders')
      await addNamedField(user, 'amount')
      await user.click(screen.getByRole('button', { name: /create collection/i }))

      await waitFor(() => {
        expect(
          screen.getByText(/creating collection and applying migrations/i),
        ).toBeInTheDocument()
      })

      resolveSubmit()
    })

    it('shows success state after collection is created', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/collection name \*/i), 'products')
      await addNamedField(user, 'title')
      await user.click(screen.getByRole('button', { name: /create collection/i }))

      await waitFor(() => {
        expect(
          screen.getByText(/collection "products" created successfully/i),
        ).toBeInTheDocument()
      })
      expect(screen.getByRole('button', { name: /done/i })).toBeInTheDocument()
    })

    it('shows API error message when onSubmit throws', async () => {
      const user = userEvent.setup()
      const apiError = new SnackBaseError('Request failed', 'CONFLICT_ERROR', 409, {
        detail: 'Collection name already exists',
      })
      const onSubmit = vi.fn().mockRejectedValue(apiError)
      renderDialog({ onSubmit })

      await user.type(screen.getByLabelText(/collection name \*/i), 'existing')
      await addNamedField(user, 'data')
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
        />,
      )

      await user.type(screen.getByLabelText(/collection name \*/i), 'done_test')
      await addNamedField(user, 'field_one')
      await user.click(screen.getByRole('button', { name: /create collection/i }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /done/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /done/i }))
      expect(onOpenChange).toHaveBeenCalledWith(false)
    })
  })
})
