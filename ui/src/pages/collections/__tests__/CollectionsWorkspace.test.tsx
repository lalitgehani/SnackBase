/**
 * Tests for Collections workspace shell (Phase 1):
 * - Nested routes and layout
 * - Browser rail search/selection
 * - Empty states
 * - Legacy records → data redirect
 * - Default tab heuristic
 * - Superadmin DDL visibility
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { Routes, Route, Navigate } from 'react-router'
import { render } from '@/test/utils'
import { server } from '@/test/mocks/server'
import { useAuthStore } from '@/stores/auth.store'
import CollectionsWorkspaceLayout from '../CollectionsWorkspaceLayout'
import CollectionEmptyState from '../CollectionEmptyState'
import CollectionNewPage from '../CollectionNewPage'
import CollectionDetailLayout from '../CollectionDetailLayout'
import CollectionDefaultTabRedirect from '../CollectionDefaultTabRedirect'
import LegacyRecordsRedirect from '../LegacyRecordsRedirect'
import SchemaTabPage from '../tabs/SchemaTabPage'
import DataTabPage from '../tabs/DataTabPage'
import RulesTabPage from '../tabs/RulesTabPage'
import AnalyticsTabPage from '../tabs/AnalyticsTabPage'

const mockCollectionList = {
  items: [
    {
      id: 'col-1',
      name: 'posts',
      table_name: 'posts',
      fields_count: 3,
      records_count: 10,
      has_public_access: false,
      created_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 'col-2',
      name: 'products',
      table_name: 'products',
      fields_count: 5,
      records_count: 0,
      has_public_access: true,
      created_at: '2026-01-02T00:00:00Z',
    },
  ],
  total: 2,
  page: 1,
  page_size: 100,
  total_pages: 1,
}

const mockCollectionFull = {
  id: 'col-1',
  name: 'posts',
  table_name: 'posts',
  schema: [
    { name: 'title', type: 'text', required: true },
    { name: 'body', type: 'text' },
  ],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const mockProductsFull = {
  ...mockCollectionFull,
  id: 'col-2',
  name: 'products',
  table_name: 'products',
}

function setupAuth(role: string = 'superadmin') {
  useAuthStore.setState({
    user: {
      id: 'user-1',
      email: 'admin@example.com',
      role,
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
    },
    account: {
      id: 'SY0000',
      slug: 'system',
      name: 'System',
      created_at: '2026-01-01T00:00:00Z',
    },
    token: 'test-token',
    refreshToken: 'refresh',
    isAuthenticated: true,
    isLoading: false,
    error: null,
  })
}

function setupHandlers(listOverrides?: Partial<typeof mockCollectionList>) {
  const listResponse = { ...mockCollectionList, ...listOverrides }

  server.use(
    http.get('/api/v1/collections', ({ request }) => {
      const url = new URL(request.url)
      // Full collection fetch by id: never hits this path (id is a path segment).
      // getCollectionByName uses search query.
      const search = url.searchParams.get('search')
      if (search === 'posts') {
        return HttpResponse.json({
          items: listResponse.items.filter((i) => i.name === 'posts'),
          total: 1,
          page: 1,
          page_size: 100,
          total_pages: 1,
        })
      }
      if (search === 'products') {
        return HttpResponse.json({
          items: listResponse.items.filter((i) => i.name === 'products'),
          total: 1,
          page: 1,
          page_size: 100,
          total_pages: 1,
        })
      }
      return HttpResponse.json(listResponse)
    }),
    http.get('/api/v1/collections/:id/rules', () =>
      HttpResponse.json({
        id: 'rule-1',
        collection_id: 'col-1',
        list_rule: null,
        view_rule: null,
        create_rule: null,
        update_rule: null,
        delete_rule: null,
        list_fields: '*',
        view_fields: '*',
        create_fields: '*',
        update_fields: '*',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }),
    ),
    http.get('/api/v1/collections/:id', ({ params }) => {
      // Skip if this is somehow the list path (defensive)
      if (params.id === 'rules') {
        return new HttpResponse(null, { status: 404 })
      }
      if (params.id === 'col-2') {
        return HttpResponse.json(mockProductsFull)
      }
      return HttpResponse.json(mockCollectionFull)
    }),
    http.get('/api/v1/records/posts', () =>
      HttpResponse.json({ items: [], total: 0, skip: 0, limit: 25 }),
    ),
    http.get('/api/v1/records/products', () =>
      HttpResponse.json({ items: [], total: 0, skip: 0, limit: 25 }),
    ),
    http.post('/api/v1/records/posts/aggregate', () =>
      HttpResponse.json({ results: [] }),
    ),
    http.post('/api/v1/records/products/aggregate', () =>
      HttpResponse.json({ results: [] }),
    ),
  )
}

function WorkspaceRoutes() {
  return (
    <Routes>
      <Route path="/admin/collections" element={<CollectionsWorkspaceLayout />}>
        <Route index element={<CollectionEmptyState />} />
        <Route path="new" element={<CollectionNewPage />} />
        <Route path=":collectionName" element={<CollectionDetailLayout />}>
          <Route index element={<CollectionDefaultTabRedirect />} />
          <Route path="schema" element={<SchemaTabPage />} />
          <Route path="data" element={<DataTabPage />} />
          <Route path="rules" element={<RulesTabPage />} />
          <Route path="analytics" element={<AnalyticsTabPage />} />
          <Route path="records" element={<LegacyRecordsRedirect />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/admin/collections" replace />} />
    </Routes>
  )
}

function renderWorkspace(initialEntry = '/admin/collections') {
  return render(<WorkspaceRoutes />, { initialEntries: [initialEntry] })
}

beforeEach(() => {
  localStorage.clear()
  vi.useFakeTimers({ shouldAdvanceTime: true })

  // jsdom does not implement matchMedia (used by useIsMobile / rail collapse)
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })

  // Persist token so axios interceptor can attach Authorization (same shape as auth store)
  localStorage.setItem(
    'auth-storage',
    JSON.stringify({
      state: {
        token: 'test-token',
        refreshToken: 'refresh',
        user: {
          id: 'user-1',
          email: 'admin@example.com',
          role: 'superadmin',
          is_active: true,
          created_at: '2026-01-01T00:00:00Z',
        },
        isAuthenticated: true,
      },
    }),
  )

  setupAuth('superadmin')
  setupHandlers()
})

afterEach(() => {
  vi.useRealTimers()
  useAuthStore.setState({
    user: null,
    account: null,
    token: null,
    refreshToken: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
  })
})

describe('CollectionsWorkspace', () => {
  describe('shell and empty state', () => {
    it('renders workspace shell with browser rail at /admin/collections', async () => {
      renderWorkspace()

      await waitFor(() => {
        expect(screen.getByTestId('collections-workspace')).toBeInTheDocument()
        expect(screen.getByTestId('collection-browser-rail')).toBeInTheDocument()
      })
    })

    it('lists collections with counts and public badge', async () => {
      renderWorkspace()

      await waitFor(() => {
        expect(screen.getByText('posts')).toBeInTheDocument()
        expect(screen.getByText('products')).toBeInTheDocument()
      })

      expect(screen.getByText(/3 fields · 10 records/i)).toBeInTheDocument()
      expect(screen.getByText(/5 fields · 0 records/i)).toBeInTheDocument()
      expect(screen.getByText('Public')).toBeInTheDocument()
    })

    it('shows select-collection empty state when collections exist', async () => {
      renderWorkspace()

      await waitFor(() => {
        expect(screen.getByTestId('collection-empty-state')).toBeInTheDocument()
        expect(screen.getByText(/select a collection/i)).toBeInTheDocument()
      })
    })

    it('shows zero-collections empty state with multi-tenant copy', async () => {
      setupHandlers({
        items: [],
        total: 0,
        total_pages: 0,
      })

      renderWorkspace()

      await waitFor(() => {
        expect(screen.getByTestId('collection-empty-state')).toBeInTheDocument()
        expect(screen.getByText(/global · multi-tenant/i)).toBeInTheDocument()
      })

      expect(screen.getByText(/account_id/i)).toBeInTheDocument()
      expect(
        screen.getByRole('button', { name: /create collection/i }),
      ).toBeInTheDocument()
      expect(
        screen.getByRole('button', { name: /import from json/i }),
      ).toBeInTheDocument()
    })
  })

  describe('browser rail', () => {
    it('filters collections by search (case-insensitive)', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      renderWorkspace()

      await waitFor(() => {
        expect(screen.getByText('posts')).toBeInTheDocument()
      })

      const search = screen.getByLabelText(/search collections/i)
      await user.type(search, 'prod')

      expect(screen.getByText('products')).toBeInTheDocument()
      expect(screen.queryByText('posts')).not.toBeInTheDocument()
    })

    it('shows filtered-empty message when search matches nothing', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      renderWorkspace()

      await waitFor(() => {
        expect(screen.getByText('posts')).toBeInTheDocument()
      })

      await user.type(screen.getByLabelText(/search collections/i), 'zzzz')

      expect(screen.getByText(/no collections match/i)).toBeInTheDocument()
    })

    it('navigates to collection on click (default tab redirect for posts → data)', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      renderWorkspace()

      await waitFor(() => {
        expect(screen.getByText('posts')).toBeInTheDocument()
      })

      await user.click(screen.getByRole('link', { name: /posts/i }))

      await waitFor(() => {
        expect(screen.getByTestId('data-tab')).toBeInTheDocument()
      })
    })

    it('default tab is schema when records_count is 0', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      renderWorkspace()

      await waitFor(() => {
        expect(screen.getByText('products')).toBeInTheDocument()
      })

      await user.click(screen.getByRole('link', { name: /products/i }))

      await waitFor(() => {
        expect(screen.getByTestId('schema-tab')).toBeInTheDocument()
      })
    })

    it('collapses and expands the rail', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      renderWorkspace()

      await waitFor(() => {
        expect(screen.getByTestId('collection-browser-rail')).toBeInTheDocument()
      })

      await user.click(screen.getByLabelText(/collapse collection browser/i))

      expect(screen.getByTestId('collection-browser-rail-collapsed')).toBeInTheDocument()

      await user.click(screen.getByLabelText(/expand collection browser/i))

      expect(screen.getByTestId('collection-browser-rail')).toBeInTheDocument()
    })

    it('shows error retry when list fails', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      server.use(
        http.get('/api/v1/collections', () =>
          HttpResponse.json({ detail: 'boom' }, { status: 500 }),
        ),
      )

      renderWorkspace()

      await waitFor(() => {
        expect(screen.getByText(/failed to load/i)).toBeInTheDocument()
      })

      // Restore success handlers (prepended ahead of the error override)
      setupHandlers()
      await user.click(screen.getByRole('button', { name: /retry/i }))

      await waitFor(() => {
        expect(screen.getByText('posts')).toBeInTheDocument()
      })
    })
  })

  describe('tabs and deep links', () => {
    it('deep-links to data tab', async () => {
      renderWorkspace('/admin/collections/posts/data')

      await waitFor(() => {
        expect(screen.getByTestId('data-tab')).toBeInTheDocument()
        expect(screen.getByTestId('collection-detail-layout')).toBeInTheDocument()
      })
    })

    it('deep-links to schema tab', async () => {
      renderWorkspace('/admin/collections/posts/schema')

      await waitFor(() => {
        expect(screen.getByTestId('schema-tab')).toBeInTheDocument()
      })
    })

    it('deep-links to rules tab', async () => {
      renderWorkspace('/admin/collections/posts/rules')

      await waitFor(() => {
        expect(screen.getByTestId('rules-tab')).toBeInTheDocument()
      })
    })

    it('deep-links to analytics tab', async () => {
      renderWorkspace('/admin/collections/posts/analytics')

      await waitFor(() => {
        expect(screen.getByTestId('analytics-tab')).toBeInTheDocument()
      })
    })

    it('redirects legacy /records to /data', async () => {
      renderWorkspace('/admin/collections/posts/records')

      await waitFor(() => {
        expect(screen.getByTestId('data-tab')).toBeInTheDocument()
      })
    })

    it('switches tabs via navigation links', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
      renderWorkspace('/admin/collections/posts/data')

      await waitFor(() => {
        expect(screen.getByTestId('data-tab')).toBeInTheDocument()
      })

      await user.click(screen.getByRole('link', { name: /^schema$/i }))

      await waitFor(() => {
        expect(screen.getByTestId('schema-tab')).toBeInTheDocument()
      })
    })
  })

  describe('header and permissions', () => {
    it('shows edit/delete for superadmin', async () => {
      renderWorkspace('/admin/collections/posts/schema')

      await waitFor(() => {
        expect(screen.getByTestId('collection-detail-layout')).toBeInTheDocument()
      })

      expect(screen.getAllByRole('button', { name: /edit schema/i }).length).toBeGreaterThan(0)
      expect(screen.getByRole('button', { name: /^delete$/i })).toBeInTheDocument()
    })

    it('hides DDL actions for non-superadmin', async () => {
      setupAuth('admin')
      renderWorkspace('/admin/collections/posts/schema')

      await waitFor(() => {
        expect(screen.getByTestId('collection-detail-layout')).toBeInTheDocument()
      })

      expect(screen.queryByRole('button', { name: /edit schema/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /^delete$/i })).not.toBeInTheDocument()
    })

    it('hides new collection for non-superadmin', async () => {
      setupAuth('admin')
      renderWorkspace()

      await waitFor(() => {
        expect(screen.getByTestId('collection-browser-rail')).toBeInTheDocument()
      })

      expect(
        screen.queryByRole('button', { name: /new collection/i }),
      ).not.toBeInTheDocument()
    })
  })

  describe('/new route', () => {
    it('opens create collection dialog', async () => {
      renderWorkspace('/admin/collections/new')

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
        expect(
          screen.getByRole('heading', { name: /create collection/i }),
        ).toBeInTheDocument()
      })
    })
  })
})
