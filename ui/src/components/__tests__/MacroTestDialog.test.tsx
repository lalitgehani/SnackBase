/**
 * Tests for MacroTestDialog component
 *
 * Verifies:
 * - Renders macro name and SQL query
 * - Shows "No parameters" when macro has no params
 * - Shows parameter input fields when macro has params
 * - Run Test button triggers testMacro service
 * - Shows success result after successful test
 * - Shows error after failed test
 * - Close button closes dialog
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { render } from '@/test/utils'
import MacroTestDialog from '@/components/macros/MacroTestDialog'
import type { Macro } from '@/types/macro'

const macro: Macro = {
  id: 42,
  name: 'count_records',
  description: 'Counts records',
  sql_query: 'SELECT COUNT(*) FROM posts',
  parameters: '[]',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  created_by: null,
}

const macroWithParams: Macro = {
  ...macro,
  id: 43,
  name: 'get_by_id',
  parameters: '["table_name", "record_id"]',
  sql_query: 'SELECT * FROM {{table_name}} WHERE id = {{record_id}}',
}

function renderDialog(props: Partial<{
  open: boolean
  onOpenChange: (open: boolean) => void
  macro: Macro | null
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    macro: m = macro,
  } = props

  return render(
    <MacroTestDialog
      open={open}
      onOpenChange={onOpenChange}
      macro={m}
    />
  )
}

describe('MacroTestDialog', () => {
  beforeEach(() => {
    server.use(
      http.post('/api/v1/macros/:id/test', () =>
        HttpResponse.json({ result: '42', execution_time: 1.5, rows_affected: 0 })
      )
    )
  })

  describe('rendering', () => {
    it('renders macro name in title', () => {
      renderDialog()
      expect(screen.getByText(/@count_records/i)).toBeInTheDocument()
    })

    it('renders SQL query preview', () => {
      renderDialog()
      expect(screen.getByText(/SELECT COUNT/i)).toBeInTheDocument()
    })

    it('shows "No parameters required" when macro has no params', () => {
      renderDialog()
      expect(screen.getByText(/no parameters required/i)).toBeInTheDocument()
    })

    it('shows parameter inputs when macro has params', () => {
      renderDialog({ macro: macroWithParams })
      expect(screen.getByLabelText('table_name')).toBeInTheDocument()
      expect(screen.getByLabelText('record_id')).toBeInTheDocument()
    })

    it('renders Run Test button', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /run test/i })).toBeInTheDocument()
    })
  })

  describe('test execution', () => {
    it('shows success result after successful test', async () => {
      const user = userEvent.setup()
      renderDialog()

      await user.click(screen.getByRole('button', { name: /run test/i }))

      await waitFor(() => {
        expect(screen.getByText(/execution successful/i)).toBeInTheDocument()
      })
      expect(screen.getByText('42')).toBeInTheDocument()
    })

    it('shows execution time after successful test', async () => {
      const user = userEvent.setup()
      renderDialog()

      await user.click(screen.getByRole('button', { name: /run test/i }))

      await waitFor(() => {
        expect(screen.getByText(/1.50 ms/i)).toBeInTheDocument()
      })
    })

    it('shows error when test fails', async () => {
      server.use(
        http.post('/api/v1/macros/:id/test', () =>
          HttpResponse.json({ detail: 'SQL syntax error' }, { status: 400 })
        )
      )

      const user = userEvent.setup()
      renderDialog()

      await user.click(screen.getByRole('button', { name: /run test/i }))

      await waitFor(() => {
        expect(screen.getByText(/execution failed/i)).toBeInTheDocument()
      })
    })
  })

  describe('close behavior', () => {
    it('calls onOpenChange(false) when Close is clicked', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      renderDialog({ onOpenChange })

      const closeButtons = screen.getAllByRole('button', { name: /close/i })
      await user.click(closeButtons[closeButtons.length - 1])
      expect(onOpenChange).toHaveBeenCalledWith(false)
    })
  })
})
