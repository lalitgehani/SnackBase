/**
 * Tests for MacroDetailDialog component
 *
 * Verifies:
 * - Returns null when macro is null
 * - Renders macro name in title
 * - Renders macro description
 * - Shows macro ID
 * - Shows parameters (or "No parameters" when none)
 * - Shows SQL query
 * - Test Macro button calls onOpenChange(false) and onTest
 * - Edit button calls onOpenChange(false) and onEdit
 * - Close button closes dialog
 */

import { describe, it, expect, vi } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import MacroDetailDialog from '@/components/macros/MacroDetailDialog'
import type { Macro } from '@/types/macro'

const macro: Macro = {
  id: 42,
  name: 'count_records',
  description: 'Counts records in a table',
  sql_query: 'SELECT COUNT(*) FROM {{table}}',
  parameters: '["table"]',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  created_by: 'admin@example.com',
}

const macroNoParams: Macro = {
  ...macro,
  id: 43,
  name: 'get_stats',
  description: null,
  parameters: '[]',
}

function renderDialog(props: Partial<{
  open: boolean
  onOpenChange: (open: boolean) => void
  macro: Macro | null
  onTest: (macro: Macro) => void
  onEdit: (macro: Macro) => void
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    macro: m = macro,
    onTest = vi.fn(),
    onEdit = vi.fn(),
  } = props

  return render(
    <MacroDetailDialog
      open={open}
      onOpenChange={onOpenChange}
      macro={m}
      onTest={onTest}
      onEdit={onEdit}
    />
  )
}

describe('MacroDetailDialog', () => {
  describe('null macro', () => {
    it('renders nothing when macro is null', () => {
      const { container } = renderDialog({ macro: null })
      expect(container).toBeEmptyDOMElement()
    })
  })

  describe('rendering', () => {
    it('renders macro name in title', () => {
      renderDialog()
      expect(screen.getByText('count_records')).toBeInTheDocument()
    })

    it('renders macro description', () => {
      renderDialog()
      expect(screen.getByText('Counts records in a table')).toBeInTheDocument()
    })

    it('shows macro ID', () => {
      renderDialog()
      expect(screen.getByText(/id: 42/i)).toBeInTheDocument()
    })

    it('shows parameter badges', () => {
      renderDialog()
      expect(screen.getByText('table')).toBeInTheDocument()
    })

    it('shows "No parameters" when macro has no params', () => {
      renderDialog({ macro: macroNoParams })
      expect(screen.getByText(/no parameters/i)).toBeInTheDocument()
    })

    it('shows SQL query', () => {
      renderDialog()
      expect(screen.getByText(/SELECT COUNT\(\*\) FROM/i)).toBeInTheDocument()
    })

    it('shows created_by', () => {
      renderDialog()
      expect(screen.getByText(/admin@example.com/i)).toBeInTheDocument()
    })
  })

  describe('actions', () => {
    it('calls onOpenChange(false) and onTest when Test Macro is clicked', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      const onTest = vi.fn()
      renderDialog({ onOpenChange, onTest })

      await user.click(screen.getByRole('button', { name: /test macro/i }))
      expect(onOpenChange).toHaveBeenCalledWith(false)
      expect(onTest).toHaveBeenCalledWith(macro)
    })

    it('calls onOpenChange(false) and onEdit when Edit is clicked', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      const onEdit = vi.fn()
      renderDialog({ onOpenChange, onEdit })

      await user.click(screen.getByRole('button', { name: /^edit$/i }))
      expect(onOpenChange).toHaveBeenCalledWith(false)
      expect(onEdit).toHaveBeenCalledWith(macro)
    })

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
