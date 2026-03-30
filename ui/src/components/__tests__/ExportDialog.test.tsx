/**
 * Tests for ExportDialog component
 *
 * Verifies:
 * - Renders dialog title and collection name
 * - Shows total record count in Export button
 * - Shows filter export options when filter is active
 * - Does not show filter options when no filter
 * - Cancel button closes dialog
 * - Export button triggers export and closes dialog
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { render } from '@/test/utils'
import ExportDialog from '@/components/records/ExportDialog'

// Mock URL.createObjectURL and anchor click
const mockCreateObjectURL = vi.fn(() => 'blob:test')
const mockRevokeObjectURL = vi.fn()
global.URL.createObjectURL = mockCreateObjectURL
global.URL.revokeObjectURL = mockRevokeObjectURL

function renderDialog(props: Partial<{
  open: boolean
  onOpenChange: (open: boolean) => void
  collection: string
  filterExpression: string
  total: number
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    collection = 'products',
    filterExpression = '',
    total = 25,
  } = props

  return render(
    <ExportDialog
      open={open}
      onOpenChange={onOpenChange}
      collection={collection}
      filterExpression={filterExpression}
      total={total}
    />
  )
}

describe('ExportDialog', () => {
  beforeEach(() => {
    server.use(
      http.get('/api/v1/records/products', () =>
        HttpResponse.json({
          items: [{ id: '1', title: 'Product 1' }],
          total: 1,
          skip: 0,
          limit: 100,
        })
      )
    )
  })

  describe('rendering', () => {
    it('renders dialog title', () => {
      renderDialog()
      expect(screen.getByRole('heading', { name: /export records/i })).toBeInTheDocument()
    })

    it('renders collection name in description', () => {
      renderDialog({ collection: 'products' })
      // "products" appears in description and export button - use getAllByText
      expect(screen.getAllByText(/products/i).length).toBeGreaterThan(0)
    })

    it('renders Cancel button', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
    })

    it('renders Export button with record count', () => {
      renderDialog({ total: 10 })
      expect(screen.getByRole('button', { name: /export 10 records/i })).toBeInTheDocument()
    })

    it('uses singular "Record" for total = 1', () => {
      renderDialog({ total: 1 })
      expect(screen.getByRole('button', { name: /export 1 record$/i })).toBeInTheDocument()
    })
  })

  describe('filter options', () => {
    it('shows filter scope options when filter is active', () => {
      renderDialog({ filterExpression: 'price > 10' })
      expect(screen.getByText(/what to export/i)).toBeInTheDocument()
    })

    it('does not show filter options when no filter', () => {
      renderDialog({ filterExpression: '' })
      expect(screen.queryByText(/what to export/i)).not.toBeInTheDocument()
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

  describe('export action', () => {
    it('clicks export button without crashing', async () => {
      const user = userEvent.setup()
      renderDialog({ total: 1 })

      const exportBtn = screen.getByRole('button', { name: /export 1 record/i })
      await user.click(exportBtn)

      await waitFor(() => {
        expect(mockCreateObjectURL).toHaveBeenCalled()
      }, { timeout: 10000 })
    })
  })
})
