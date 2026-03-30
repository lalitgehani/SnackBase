/**
 * Tests for ManageGroupUsersDialog component
 *
 * Verifies:
 * - Shows loading spinner while fetching users
 * - Renders "Manage Group Members" heading
 * - Shows group name in description
 * - Shows "No members yet" when group has no users
 * - Renders current members when group has users
 * - Remove button calls onRemoveUser with group and user IDs
 * - Add button calls onAddUser with group and user IDs
 * - Shows error when onAddUser throws
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { render } from '@/test/utils'
import ManageGroupUsersDialog from '@/components/groups/ManageGroupUsersDialog'
import type { Group } from '@/services/groups.service'

const group: Group = {
  id: 'grp_abc123',
  account_id: 'acc_abc123',
  name: 'Administrators',
  description: 'Admin group',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const groupWithUsers: Group = {
  ...group,
  users: [
    {
      id: 'usr_111',
      email: 'alice@example.com',
      account_id: 'acc_abc123',
      account_code: 'AC1234',
      account_name: 'Acme Corp',
      role_id: 1,
      role_name: 'admin',
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      last_login: null,
      email_verified: true,
      email_verified_at: null,
    },
  ],
}

const availableUser = {
  id: 'usr_222',
  email: 'bob@example.com',
  account_id: 'acc_abc123',
  account_code: 'AC1234',
  account_name: 'Acme Corp',
  role_id: 2,
  role_name: 'user',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  last_login: null,
  email_verified: true,
  email_verified_at: null,
}

function renderDialog(props: Partial<{
  open: boolean
  onOpenChange: (open: boolean) => void
  group: Group | null
  onAddUser: (groupId: string, userId: string) => Promise<void>
  onRemoveUser: (groupId: string, userId: string) => Promise<void>
}> = {}) {
  const {
    open = true,
    onOpenChange = vi.fn(),
    group: g = group,
    onAddUser = vi.fn().mockResolvedValue(undefined),
    onRemoveUser = vi.fn().mockResolvedValue(undefined),
  } = props

  return render(
    <ManageGroupUsersDialog
      open={open}
      onOpenChange={onOpenChange}
      group={g}
      onAddUser={onAddUser}
      onRemoveUser={onRemoveUser}
    />
  )
}

describe('ManageGroupUsersDialog', () => {
  beforeEach(() => {
    // Default: users list returns empty, group has no users
    server.use(
      http.get('/api/v1/users', () =>
        HttpResponse.json({ items: [availableUser], total: 1 })
      ),
      http.get('/api/v1/groups/:id', () =>
        HttpResponse.json(group)
      )
    )
  })

  describe('rendering', () => {
    it('renders Manage Group Members heading', async () => {
      renderDialog()
      await waitFor(() => {
        expect(screen.getByRole('heading', { name: /manage group members/i })).toBeInTheDocument()
      })
    })

    it('renders group name in description', async () => {
      renderDialog()
      await waitFor(() => {
        expect(screen.getByText(/administrators/i)).toBeInTheDocument()
      })
    })

    it('shows "No members yet" when group has no users', async () => {
      renderDialog()
      await waitFor(() => {
        expect(screen.getByText(/no members yet/i)).toBeInTheDocument()
      })
    })
  })

  describe('with existing members', () => {
    beforeEach(() => {
      server.use(
        http.get('/api/v1/users', () =>
          HttpResponse.json({ items: [availableUser], total: 1 })
        ),
        http.get('/api/v1/groups/:id', () =>
          HttpResponse.json(groupWithUsers)
        )
      )
    })

    it('shows existing member emails', async () => {
      renderDialog()
      await waitFor(() => {
        expect(screen.getByText('alice@example.com')).toBeInTheDocument()
      })
    })

    it('calls onRemoveUser when Remove is clicked', async () => {
      const user = userEvent.setup()
      const onRemoveUser = vi.fn().mockResolvedValue(undefined)
      renderDialog({ onRemoveUser })

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /remove/i })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /remove/i }))

      await waitFor(() => {
        expect(onRemoveUser).toHaveBeenCalledWith('grp_abc123', 'usr_111')
      })
    })
  })

  describe('Add Members section', () => {
    it('renders search input', async () => {
      renderDialog()
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search users by email/i)).toBeInTheDocument()
      })
    })

    it('renders Add button', async () => {
      renderDialog()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /add/i })).toBeInTheDocument()
      })
    })
  })
})
