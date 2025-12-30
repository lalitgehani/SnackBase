/**
 * Users management page
 * Superadmin-only page for managing users across all accounts
 */

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import {
  Plus,
  RefreshCw,
  Users as UsersIcon,
  Pencil,
  Key,
  UserX,
  Search,
} from 'lucide-react';
import CreateUserDialog from '@/components/users/CreateUserDialog';
import EditUserDialog from '@/components/users/EditUserDialog';
import ResetPasswordDialog from '@/components/users/ResetPasswordDialog';
import DeactivateUserDialog from '@/components/users/DeactivateUserDialog';
import {
  getUsers,
  createUser,
  updateUser,
  resetUserPassword,
  deactivateUser,
  type User,
  type UserListParams,
  type CreateUserRequest,
  type UpdateUserRequest,
} from '@/services/users.service';
import { getAccounts, type AccountListItem } from '@/services/accounts.service';
import { getRoles, type RoleListItem } from '@/services/roles.service';
import { handleApiError } from '@/lib/api';
import { DataTable, type Column } from '@/components/common/DataTable';

export default function UsersPage() {
  const [data, setData] = useState<User[] | null>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [accountId, setAccountId] = useState<string>('all_accounts');
  const [roleId, setRoleId] = useState<string>('all_roles');
  const [isActive, setIsActive] = useState<string>('all_status');
  const [search, setSearch] = useState('');

  // Pagination
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Dialog state
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [resetPasswordDialogOpen, setResetPasswordDialogOpen] = useState(false);
  const [deactivateDialogOpen, setDeactivateDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  // Dropdown data
  const [accounts, setAccounts] = useState<AccountListItem[]>([]);
  const [roles, setRoles] = useState<RoleListItem[]>([]);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params: UserListParams = {
        skip: (page - 1) * pageSize,
        limit: pageSize,
        sort: '-created_at',
      };

      if (accountId && accountId !== 'all_accounts') params.account_id = accountId;
      if (roleId && roleId !== 'all_roles') params.role_id = parseInt(roleId);
      if (isActive && isActive !== 'all_status') params.is_active = isActive === 'true';
      if (search) params.search = search;

      const response = await getUsers(params);
      setData(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  }, [accountId, roleId, isActive, search, page, pageSize]);

  const fetchDropdownData = async () => {
    try {
      const [accountsRes, rolesRes] = await Promise.all([
        getAccounts({ page_size: 100 }),
        getRoles(),
      ]);
      setAccounts(accountsRes.items);
      setRoles(rolesRes.items);
    } catch (err) {
      console.error('Failed to load dropdown data:', err);
    }
  };

  useEffect(() => {
    fetchUsers();
    fetchDropdownData();
  }, [fetchUsers]);

  const handleCreateUser = async (data: CreateUserRequest) => {
    await createUser(data);
    await fetchUsers();
  };

  const handleUpdateUser = async (userId: string, data: UpdateUserRequest) => {
    await updateUser(userId, data);
    await fetchUsers();
  };

  const handleResetPassword = async (userId: string, data: { new_password: string }) => {
    await resetUserPassword(userId, data);
  };

  const handleDeactivateUser = async (userId: string) => {
    await deactivateUser(userId);
    await fetchUsers();
  };

  const handleEdit = (user: User) => {
    setSelectedUser(user);
    setEditDialogOpen(true);
  };

  const handleResetPasswordClick = (user: User) => {
    setSelectedUser(user);
    setResetPasswordDialogOpen(true);
  };

  const handleDeactivateClick = (user: User) => {
    setSelectedUser(user);
    setDeactivateDialogOpen(true);
  };

  const columns: Column<User>[] = [
    {
      header: 'Email',
      accessorKey: 'email',
      className: 'font-medium'
    },
    {
      header: 'Account',
      render: (user) => (
        <div>
          <div>{user.account_name}</div>
          <div className="text-xs text-muted-foreground">{user.account_code}</div>
        </div>
      )
    },
    {
      header: 'Role',
      render: (user) => <Badge variant="secondary">{user.role_name}</Badge>
    },
    {
      header: 'Status',
      render: (user) => (
        <Badge variant={user.is_active ? 'default' : 'secondary'}>
          {user.is_active ? 'Active' : 'Inactive'}
        </Badge>
      )
    },
    {
      header: 'Created',
      render: (user) => <span>{new Date(user.created_at).toLocaleDateString()}</span>
    },
    {
      header: 'Last Login',
      render: (user) => (
        <span>
          {user.last_login
            ? new Date(user.last_login).toLocaleDateString()
            : 'Never'}
        </span>
      )
    },
    {
      header: 'Actions',
      className: 'text-right',
      render: (user) => (
        <div className="flex justify-end gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={(e) => {
              e.stopPropagation();
              handleEdit(user);
            }}
            title="Edit user"
          >
            <Pencil className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={(e) => {
              e.stopPropagation();
              handleResetPasswordClick(user);
            }}
            title="Reset password"
          >
            <Key className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={(e) => {
              e.stopPropagation();
              handleDeactivateClick(user);
            }}
            title="Deactivate user"
            className="text-destructive hover:text-destructive"
            disabled={!user.is_active}
          >
            <UserX className="h-4 w-4" />
          </Button>
        </div>
      )
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Users</h1>
          <p className="text-muted-foreground mt-2">Manage users across all accounts</p>
        </div>
        <Button onClick={() => setCreateDialogOpen(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          Create User
        </Button>
      </div>

      {/* Users Management */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UsersIcon className="h-5 w-5 text-primary" />
            User Management
          </CardTitle>
          <CardDescription>
            View and manage users, reset passwords, and deactivate accounts
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Filters and Refresh */}
          <div className="flex flex-wrap items-end gap-4">
            <div className="space-y-2">
              <Label htmlFor="search">Search</Label>
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="search"
                  placeholder="Search by email..."
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(1); // Reset page on filter change
                  }}
                  className="pl-8 w-64"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="account">Account</Label>
              <Select
                value={accountId}
                onValueChange={(v) => {
                  setAccountId(v);
                  setPage(1);
                }}
              >
                <SelectTrigger id="account" className="w-48">
                  <SelectValue placeholder="All accounts" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all_accounts">All accounts</SelectItem>
                  {accounts.map((account) => (
                    <SelectItem key={account.id} value={account.id}>
                      {account.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <Select
                value={roleId}
                onValueChange={(v) => {
                  setRoleId(v);
                  setPage(1);
                }}
              >
                <SelectTrigger id="role" className="w-40">
                  <SelectValue placeholder="All roles" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all_roles">All roles</SelectItem>
                  {roles.map((role) => (
                    <SelectItem key={role.id} value={role.id.toString()}>
                      {role.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
              <Select
                value={isActive}
                onValueChange={(v) => {
                  setIsActive(v);
                  setPage(1);
                }}
              >
                <SelectTrigger id="status" className="w-32">
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all_status">All</SelectItem>
                  <SelectItem value="true">Active</SelectItem>
                  <SelectItem value="false">Inactive</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="ml-auto">
              <Button variant="outline" size="icon" onClick={fetchUsers} disabled={loading}>
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>

          {/* Error State */}
          {error && (
            <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
              <p className="text-destructive font-medium">Failed to load users</p>
              <p className="text-sm text-muted-foreground mt-1">{error}</p>
              <Button onClick={fetchUsers} className="mt-4" size="sm">
                Try Again
              </Button>
            </div>
          )}

          {/* Loading State */}
          {loading && !data && (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          )}

          {/* Table */}


          {/* Empty State visual embedded in DataTable if noDataMessage is simple string, but here we had actions.
              DataTable supports complex noDataMessage? Currently it takes string.
              But if data is empty, DataTable shows noDataMessage.
              If we want the specific empty state with "Create User" button, we might need a custom empty state in DataTable or just wrap it.
              Actually, the original code had a nice empty state.
              DataTable implementation:
                ) : data.length === 0 ? (
                    <TableRow>
                        <TableCell colSpan={columns.length} className="h-24 text-center text-muted-foreground">
                            {noDataMessage}
                        </TableCell>
                    </TableRow>
              It's simple. 
              If I want strict parity, I should probably handle empty state outside if I want buttons.
              But `DataTable` handles the "No data" row.
              If `data` is empty, generic table shows "No data found" or custom message.
              The original empty state had a button "Create User".
              I'll just pass a simple message for now to `DataTable`. 
              Or I can conditionally render `DataTable` only if `data.length > 0`.
              Start simple.
          */}
          {!loading && data && data.length === 0 && (
            <div className="text-center py-12">
              <UsersIcon className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
              <h3 className="text-lg font-medium mb-2">No users found</h3>
              <p className="text-muted-foreground mb-4">
                {search || accountId || roleId || isActive
                  ? 'Try adjusting your filters'
                  : 'Get started by creating your first user'}
              </p>
              <Button onClick={() => setCreateDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create User
              </Button>
            </div>
          )}

          {/* We only render DataTable if data.length > 0 to preserve the custom empty state which has a button */}
          {!loading && data && data.length > 0 && (
            <DataTable
              data={data}
              columns={columns}
              keyExtractor={(user) => user.id}
              totalItems={total}
              pagination={{
                page,
                pageSize,
                onPageChange: setPage,
                onPageSizeChange: (size) => {
                  setPageSize(size);
                  setPage(1);
                }
              }}
            />
          )}

        </CardContent>
      </Card>

      {/* Dialogs */}
      <CreateUserDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSubmit={handleCreateUser}
      />

      <EditUserDialog
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        user={selectedUser}
        onSubmit={handleUpdateUser}
      />

      <ResetPasswordDialog
        open={resetPasswordDialogOpen}
        onOpenChange={setResetPasswordDialogOpen}
        user={selectedUser}
        onSubmit={handleResetPassword}
      />

      <DeactivateUserDialog
        open={deactivateDialogOpen}
        onOpenChange={setDeactivateDialogOpen}
        user={selectedUser}
        onSubmit={handleDeactivateUser}
      />
    </div>
  );
}
