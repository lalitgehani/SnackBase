/**
 * Tests for MacrosTable component
 *
 * Verifies:
 * - Shows "No macros found" when empty
 * - Renders macro names with @ prefix
 * - Renders macro descriptions (and "No description" fallback)
 * - Renders parameter count badge
 * - Actions dropdown: View Details, Test Macro, Edit, Delete
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import MacrosTable from '@/components/macros/MacrosTable'
import type { Macro } from '@/types/macro'

const macros: Macro[] = [
  {
    id: 1,
    name: 'count_records',
    description: 'Count all records',
    sql_query: 'SELECT COUNT(*) FROM posts',
    parameters: '["table"]',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T10:00:00Z',
    created_by: null,
  },
  {
    id: 2,
    name: 'get_stats',
    description: null,
    sql_query: 'SELECT * FROM stats',
    parameters: '[]',
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T10:00:00Z',
    created_by: null,
  },
]

function renderTable(props: Partial<{
  macros: Macro[]
  onView: (macro: Macro) => void
  onEdit: (macro: Macro) => void
  onDelete: (macro: Macro) => void
  onTest: (macro: Macro) => void
}> = {}) {
  const {
    macros: m = macros,
    onView = vi.fn(),
    onEdit = vi.fn(),
    onDelete = vi.fn(),
    onTest = vi.fn(),
  } = props

  return render(
    <MacrosTable
      macros={m}
      onView={onView}
      onEdit={onEdit}
      onDelete={onDelete}
      onTest={onTest}
    />
  )
}

describe('MacrosTable', () => {
  describe('empty state', () => {
    it('shows "No macros found" when empty', () => {
      renderTable({ macros: [] })
      expect(screen.getByText(/no macros found/i)).toBeInTheDocument()
    })
  })

  describe('rendering', () => {
    it('renders macro names with @ prefix', () => {
      renderTable()
      expect(screen.getByText('count_records')).toBeInTheDocument()
      expect(screen.getByText('get_stats')).toBeInTheDocument()
    })

    it('renders macro descriptions', () => {
      renderTable()
      expect(screen.getByText('Count all records')).toBeInTheDocument()
    })

    it('shows "No description" fallback for null descriptions', () => {
      renderTable()
      expect(screen.getByText(/no description/i)).toBeInTheDocument()
    })

    it('renders parameter count badges', () => {
      renderTable()
      // First macro has 1 param, second has 0
      expect(screen.getByText('1')).toBeInTheDocument()
      expect(screen.getByText('0')).toBeInTheDocument()
    })
  })

  describe('actions dropdown', () => {
    async function openDropdown(index = 0) {
      const user = userEvent.setup()
      const triggers = screen.getAllByRole('button', { name: /open menu/i })
      await user.click(triggers[index])
      return user
    }

    it('calls onView when View Details is clicked', async () => {
      const onView = vi.fn()
      renderTable({ onView })

      const user = await openDropdown(0)
      await user.click(screen.getByText('View Details'))
      expect(onView).toHaveBeenCalledWith(macros[0])
    })

    it('calls onTest when Test Macro is clicked', async () => {
      const onTest = vi.fn()
      renderTable({ onTest })

      const user = await openDropdown(0)
      await user.click(screen.getByText('Test Macro'))
      expect(onTest).toHaveBeenCalledWith(macros[0])
    })

    it('calls onEdit when Edit is clicked', async () => {
      const onEdit = vi.fn()
      renderTable({ onEdit })

      const user = await openDropdown(0)
      await user.click(screen.getByText('Edit'))
      expect(onEdit).toHaveBeenCalledWith(macros[0])
    })

    it('calls onDelete when Delete is clicked', async () => {
      const onDelete = vi.fn()
      renderTable({ onDelete })

      const user = await openDropdown(0)
      await user.click(screen.getByText('Delete'))
      expect(onDelete).toHaveBeenCalledWith(macros[0])
    })
  })
})
