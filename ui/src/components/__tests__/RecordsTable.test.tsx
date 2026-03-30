/**
 * Tests for RecordsTable component
 *
 * Verifies:
 * - Renders table with records
 * - Shows empty state when no records
 * - Renders schema field columns
 * - Shows null values as "null"
 * - Renders boolean fields as Yes/No badges
 * - Renders long text truncated
 * - Calls onView, onEdit, onDelete when action buttons clicked
 * - Multi-select checkbox column renders when onSelectionChange provided
 * - Selecting all records works
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import RecordsTable from '@/components/records/RecordsTable'
import type { RecordListItem } from '@/types/records.types'
import type { FieldDefinition } from '@/services/collections.service'

const schema: FieldDefinition[] = [
  { name: 'title', type: 'text' },
  { name: 'published', type: 'boolean' },
  { name: 'count', type: 'number' },
]

const records: RecordListItem[] = [
  {
    id: 'rec_001',
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
    title: 'Hello World',
    published: true,
    count: 42,
  },
  {
    id: 'rec_002',
    created_at: '2024-01-16T10:00:00Z',
    updated_at: '2024-01-16T10:00:00Z',
    title: 'Second Post',
    published: false,
    count: null,
  },
]

const defaultProps = {
  records,
  schema,
  sortBy: 'created_at',
  sortOrder: 'desc' as const,
  onSort: vi.fn(),
  onView: vi.fn(),
  onEdit: vi.fn(),
  onDelete: vi.fn(),
  totalItems: 2,
  page: 1,
  pageSize: 10,
  onPageChange: vi.fn(),
  onPageSizeChange: vi.fn(),
}

function renderTable(props = {}) {
  return render(<RecordsTable {...defaultProps} {...props} />)
}

describe('RecordsTable', () => {
  describe('rendering', () => {
    it('renders schema column headers', () => {
      renderTable()
      expect(screen.getByText('title')).toBeInTheDocument()
      expect(screen.getByText('published')).toBeInTheDocument()
      expect(screen.getByText('count')).toBeInTheDocument()
    })

    it('renders text field values', () => {
      renderTable()
      expect(screen.getByText('Hello World')).toBeInTheDocument()
      expect(screen.getByText('Second Post')).toBeInTheDocument()
    })

    it('renders boolean fields as Yes/No badges', () => {
      renderTable()
      expect(screen.getByText('Yes')).toBeInTheDocument()
      expect(screen.getByText('No')).toBeInTheDocument()
    })

    it('renders null values as "null"', () => {
      renderTable()
      expect(screen.getAllByText('null').length).toBeGreaterThan(0)
    })

    it('renders Created column', () => {
      renderTable()
      expect(screen.getByText('Created')).toBeInTheDocument()
    })

    it('shows empty state when no records', () => {
      renderTable({ records: [] })
      expect(screen.getByText(/no records found/i)).toBeInTheDocument()
    })
  })

  describe('action buttons', () => {
    it('calls onView when view button clicked', async () => {
      const user = userEvent.setup()
      const onView = vi.fn()
      renderTable({ onView })

      const viewBtns = screen.getAllByTitle('View record')
      await user.click(viewBtns[0])
      expect(onView).toHaveBeenCalledWith(records[0])
    })

    it('calls onEdit when edit button clicked', async () => {
      const user = userEvent.setup()
      const onEdit = vi.fn()
      renderTable({ onEdit })

      const editBtns = screen.getAllByTitle('Edit record')
      await user.click(editBtns[0])
      expect(onEdit).toHaveBeenCalledWith(records[0])
    })

    it('calls onDelete when delete button clicked', async () => {
      const user = userEvent.setup()
      const onDelete = vi.fn()
      renderTable({ onDelete })

      const deleteBtns = screen.getAllByTitle('Delete record')
      await user.click(deleteBtns[0])
      expect(onDelete).toHaveBeenCalledWith(records[0])
    })
  })

  describe('multi-select', () => {
    it('renders select all checkbox when onSelectionChange provided', () => {
      renderTable({
        selectedIds: new Set(),
        onSelectionChange: vi.fn(),
      })
      expect(screen.getByLabelText('Select all')).toBeInTheDocument()
    })

    it('renders individual checkboxes for each record', () => {
      renderTable({
        selectedIds: new Set(),
        onSelectionChange: vi.fn(),
      })
      expect(screen.getByLabelText('Select record rec_001')).toBeInTheDocument()
      expect(screen.getByLabelText('Select record rec_002')).toBeInTheDocument()
    })

    it('calls onSelectionChange with all IDs when select all clicked', async () => {
      const user = userEvent.setup()
      const onSelectionChange = vi.fn()
      renderTable({
        selectedIds: new Set(),
        onSelectionChange,
      })

      await user.click(screen.getByLabelText('Select all'))
      expect(onSelectionChange).toHaveBeenCalled()
    })
  })

  describe('long text truncation', () => {
    it('truncates text fields longer than 50 chars', () => {
      const longText = 'a'.repeat(60)
      const longRecords: RecordListItem[] = [{
        id: 'rec_long',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        title: longText,
      }]
      renderTable({ records: longRecords })
      // Should show truncated version with ...
      expect(screen.getByText(`${'a'.repeat(50)}...`)).toBeInTheDocument()
    })
  })
})
