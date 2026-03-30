/**
 * Tests for ImportCollectionsDialog component
 *
 * Verifies:
 * - Renders upload step with file select button
 * - Shows error for non-JSON file
 * - Shows error for invalid JSON structure
 * - Transitions to preview after valid file upload
 * - Shows collections from preview
 * - Import Collections button calls service and shows results
 * - Cancel button closes dialog
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { render } from '@/test/utils'
import ImportCollectionsDialog from '@/components/collections/ImportCollectionsDialog'

const validExportData = {
  version: '1.0',
  exported_at: '2024-01-01T00:00:00Z',
  exported_by: 'admin@example.com',
  collections: [
    { name: 'posts', schema: [{ name: 'title', type: 'text' }] },
    { name: 'comments', schema: [{ name: 'body', type: 'text' }, { name: 'author', type: 'text' }] },
  ],
}

const importResult = {
  imported_count: 2,
  updated_count: 0,
  skipped_count: 0,
  failed_count: 0,
  collections: [
    { name: 'posts', status: 'imported', message: 'Created successfully' },
    { name: 'comments', status: 'imported', message: 'Created successfully' },
  ],
  migrations_created: [],
}

function createJsonFile(data: object, name = 'export.json') {
  const blob = new Blob([JSON.stringify(data)], { type: 'application/json' })
  return new File([blob], name, { type: 'application/json' })
}

function renderDialog(props: Partial<{
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    onSuccess = vi.fn(),
  } = props

  return render(
    <ImportCollectionsDialog
      open={open}
      onOpenChange={onOpenChange}
      onSuccess={onSuccess}
    />
  )
}

describe('ImportCollectionsDialog', () => {
  beforeEach(() => {
    server.use(
      http.post('/api/v1/collections/import', () =>
        HttpResponse.json(importResult)
      )
    )
  })

  describe('upload step', () => {
    it('renders Import Collections title', () => {
      renderDialog()
      expect(screen.getByRole('heading', { name: /import collections/i })).toBeInTheDocument()
    })

    it('renders Select JSON File button', () => {
      renderDialog()
      expect(screen.getByRole('button', { name: /select json file/i })).toBeInTheDocument()
    })

    it('shows error for non-JSON file', async () => {
      renderDialog()
      const input = document.getElementById('import-file-input') as HTMLInputElement
      const txtFile = new File(['hello'], 'data.txt', { type: 'text/plain' })
      fireEvent.change(input, { target: { files: [txtFile] } })

      await waitFor(() => {
        expect(screen.getByText(/please select a json file/i)).toBeInTheDocument()
      })
    })

    it('shows error for invalid JSON structure', async () => {
      renderDialog()
      const input = document.getElementById('import-file-input') as HTMLInputElement
      const badFile = new File([JSON.stringify({ bad: 'data' })], 'bad.json', { type: 'application/json' })
      fireEvent.change(input, { target: { files: [badFile] } })

      await waitFor(() => {
        expect(screen.getByText(/invalid export file format/i)).toBeInTheDocument()
      })
    })

    it('transitions to preview after valid JSON file upload', async () => {
      renderDialog()
      const input = document.getElementById('import-file-input') as HTMLInputElement
      const file = createJsonFile(validExportData)
      fireEvent.change(input, { target: { files: [file] } })

      await waitFor(() => {
        expect(screen.getByText('posts')).toBeInTheDocument()
        expect(screen.getByText('comments')).toBeInTheDocument()
      })
    })

    it('calls onOpenChange(false) when Cancel is clicked', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      renderDialog({ onOpenChange })

      await user.click(screen.getByRole('button', { name: /cancel/i }))
      expect(onOpenChange).toHaveBeenCalledWith(false)
    })
  })

  describe('preview step', () => {
    async function goToPreview() {
      const { ...rest } = renderDialog()
      const input = document.getElementById('import-file-input') as HTMLInputElement
      const file = createJsonFile(validExportData)
      fireEvent.change(input, { target: { files: [file] } })
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /import collections/i })).toBeInTheDocument()
      })
      return rest
    }

    it('shows collection names in preview', async () => {
      await goToPreview()
      expect(screen.getByText('posts')).toBeInTheDocument()
    })

    it('shows Back button in preview', async () => {
      await goToPreview()
      expect(screen.getByRole('button', { name: /back/i })).toBeInTheDocument()
    })

    it('imports and shows results after clicking Import Collections', async () => {
      const user = userEvent.setup()
      await goToPreview()

      await user.click(screen.getByRole('button', { name: /import collections/i }))

      await waitFor(() => {
        // Results step shows imported count
        expect(screen.getByText(/imported/i)).toBeInTheDocument()
      })
    })

    it('calls onSuccess after successful import', async () => {
      const user = userEvent.setup()
      const onSuccess = vi.fn()
      renderDialog({ onSuccess })

      const input = document.getElementById('import-file-input') as HTMLInputElement
      const file = createJsonFile(validExportData)
      fireEvent.change(input, { target: { files: [file] } })
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /import collections/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /import collections/i }))

      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalled()
      })
    })
  })
})
