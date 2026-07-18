/**
 * Schema tab dirty-state edit tests (Phase 2)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { render } from '@/test/utils'
import SchemaTabPage from '@/pages/collections/tabs/SchemaTabPage'
import {
  CollectionDetailProvider,
  type CollectionDetailContextValue,
} from '@/pages/collections/CollectionDetailContext'
import { CollectionsWorkspaceProvider } from '@/pages/collections/CollectionsWorkspaceContext'
import { useAuthStore } from '@/stores/auth.store'
import type { Collection } from '@/services/collections.service'

const collection: Collection = {
  id: 'col_1',
  name: 'products',
  table_name: 'products',
  schema: [
    { name: 'title', type: 'text', required: true },
    { name: 'price', type: 'number' },
  ],
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

function setupAuth() {
  useAuthStore.setState({
    user: {
      id: 'u1',
      email: 'admin@test.com',
      role: 'superadmin',
      account_id: 'SY0000',
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
    },
    accessToken: 'token',
    isAuthenticated: true,
  } as never)
}

function renderSchemaTab(overrides: Partial<CollectionDetailContextValue> = {}) {
  setupAuth()
  server.use(
    http.get('/api/v1/collections', () =>
      HttpResponse.json({
        items: [
          {
            id: 'col_1',
            name: 'products',
            table_name: 'products',
            fields_count: 2,
            records_count: 0,
            has_public_access: false,
            created_at: '2024-01-01T00:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        page_size: 100,
        total_pages: 1,
      }),
    ),
    http.put('/api/v1/collections/:id', async ({ request }) => {
      const body = (await request.json()) as { schema: unknown[] }
      return HttpResponse.json({
        ...collection,
        schema: body.schema,
        updated_at: '2024-01-02T00:00:00Z',
      })
    }),
  )

  const value: CollectionDetailContextValue = {
    collection,
    listItem: undefined,
    collectionName: 'products',
    loading: false,
    error: null,
    refreshDetail: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  }

  return render(
    <CollectionsWorkspaceProvider>
      <CollectionDetailProvider value={value}>
        <SchemaTabPage />
      </CollectionDetailProvider>
    </CollectionsWorkspaceProvider>,
  )
}

describe('SchemaTabPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders system fields and existing schema', async () => {
    renderSchemaTab()
    expect(screen.getByTestId('schema-tab')).toBeInTheDocument()
    expect(screen.getByTestId('system-fields-panel')).toBeInTheDocument()
    expect(screen.getByDisplayValue('title')).toBeDisabled()
    expect(screen.getByDisplayValue('price')).toBeDisabled()
  })

  it('shows dirty bar after adding a field', async () => {
    const user = userEvent.setup()
    renderSchemaTab()

    await user.click(screen.getByRole('button', { name: /add field/i }))

    await waitFor(() => {
      expect(screen.getByTestId('schema-dirty-bar')).toBeInTheDocument()
    })
    expect(screen.getByText(/unsaved schema changes/i)).toBeInTheDocument()
  })

  it('discards draft changes', async () => {
    const user = userEvent.setup()
    renderSchemaTab()

    await user.click(screen.getByRole('button', { name: /add field/i }))
    expect(screen.getByTestId('schema-dirty-bar')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /discard/i }))

    await waitFor(() => {
      expect(screen.queryByTestId('schema-dirty-bar')).not.toBeInTheDocument()
    })
    expect(screen.getByDisplayValue('title')).toBeInTheDocument()
    expect(screen.getByDisplayValue('price')).toBeInTheDocument()
    expect(screen.queryByLabelText(/field 3 name/i)).not.toBeInTheDocument()
  })

  it('saves new field via updateCollection', async () => {
    const user = userEvent.setup()
    const refreshDetail = vi.fn().mockResolvedValue(undefined)
    renderSchemaTab({ refreshDetail })

    await user.click(screen.getByRole('button', { name: /add field/i }))
    await user.type(screen.getByLabelText(/field 3 name/i), 'sku')

    await user.click(screen.getByRole('button', { name: /^save$/i }))

    await waitFor(() => {
      expect(refreshDetail).toHaveBeenCalled()
    })
  })
})
