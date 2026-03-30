/**
 * Tests for CollectionsTable component
 *
 * Verifies:
 * - Renders table headers
 * - Renders collection rows with name, field count, record count
 * - Shows Public badge for public collections
 * - View, Edit, Delete action buttons per row
 * - Calls onView when View button is clicked
 * - Calls onEdit when Edit button is clicked
 * - Calls onDelete when Delete button is clicked
 * - Shows empty state when no collections
 */

import { describe, it, expect, vi } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import CollectionsTable from '@/components/collections/CollectionsTable'
import type { CollectionListItem } from '@/services/collections.service'

const collections: CollectionListItem[] = [
  {
    id: 'col_abc123',
    name: 'products',
    table_name: 'products',
    fields_count: 3,
    records_count: 100,
    has_public_access: false,
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'col_def456',
    name: 'categories',
    table_name: 'categories',
    fields_count: 2,
    records_count: 10,
    has_public_access: true,
    created_at: '2024-01-02T00:00:00Z',
  },
]

function renderTable(props: Partial<{
  collections: CollectionListItem[]
  onView: (c: CollectionListItem) => void
  onEdit: (c: CollectionListItem) => void
  onDelete: (c: CollectionListItem) => void
  onManageRecords: (c: CollectionListItem) => void
  totalItems: number
  page: number
  pageSize: number
}> = {}) {
  const {
    collections: cols = collections,
    onView = vi.fn(),
    onEdit = vi.fn(),
    onDelete = vi.fn(),
    onManageRecords = vi.fn(),
    totalItems = collections.length,
    page = 1,
    pageSize = 10,
  } = props

  return render(
    <CollectionsTable
      collections={cols}
      sortBy="name"
      sortOrder="asc"
      onSort={vi.fn()}
      onView={onView}
      onEdit={onEdit}
      onDelete={onDelete}
      onManageRecords={onManageRecords}
      totalItems={totalItems}
      page={page}
      pageSize={pageSize}
      onPageChange={vi.fn()}
      onPageSizeChange={vi.fn()}
    />
  )
}

describe('CollectionsTable', () => {
  describe('rendering', () => {
    it('renders table column headers', () => {
      renderTable()
      expect(screen.getByText('Name')).toBeInTheDocument()
      expect(screen.getByText('Fields')).toBeInTheDocument()
      expect(screen.getByText('Records')).toBeInTheDocument()
    })

    it('renders collection names in rows', () => {
      renderTable()
      expect(screen.getByText('products')).toBeInTheDocument()
      expect(screen.getByText('categories')).toBeInTheDocument()
    })

    it('renders fields count for each collection', () => {
      renderTable()
      expect(screen.getByText('3')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument()
    })

    it('renders records count for each collection', () => {
      renderTable()
      expect(screen.getByText('100')).toBeInTheDocument()
      // "10" may appear in records count AND page size - use getAllByText
      expect(screen.getAllByText('10').length).toBeGreaterThan(0)
    })

    it('shows Public badge for public collections', () => {
      renderTable()
      expect(screen.getByText('Public')).toBeInTheDocument()
    })

    it('does not show Public badge for non-public collections', () => {
      renderTable({ collections: [collections[0]] })
      expect(screen.queryByText('Public')).not.toBeInTheDocument()
    })
  })

  describe('action buttons', () => {
    it('calls onView when view button is clicked', async () => {
      const user = userEvent.setup()
      const onView = vi.fn()
      renderTable({ onView })

      const viewButtons = screen.getAllByTitle('View schema')
      await user.click(viewButtons[0])
      expect(onView).toHaveBeenCalledWith(collections[0])
    })

    it('calls onEdit when edit button is clicked', async () => {
      const user = userEvent.setup()
      const onEdit = vi.fn()
      renderTable({ onEdit })

      const editButtons = screen.getAllByTitle('Edit schema')
      await user.click(editButtons[0])
      expect(onEdit).toHaveBeenCalledWith(collections[0])
    })

    it('calls onDelete when delete button is clicked', async () => {
      const user = userEvent.setup()
      const onDelete = vi.fn()
      renderTable({ onDelete })

      const deleteButtons = screen.getAllByTitle('Delete collection')
      await user.click(deleteButtons[0])
      expect(onDelete).toHaveBeenCalledWith(collections[0])
    })
  })

  describe('empty state', () => {
    it('shows empty state when no collections', () => {
      renderTable({ collections: [], totalItems: 0 })
      // DataTable renders "No data found" text in a table cell
      const cell = document.querySelector('td')
      expect(cell?.textContent).toContain('No collections found')
    })
  })
})
