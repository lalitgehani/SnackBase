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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  Plus,
  RefreshCw,
  Users as UsersIcon,
  Pencil,
  Key,
  UserX,
  Search,
  ChevronLeft,
  ChevronRight,
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
  const [skip, setSkip] = useState(0);
  const limit = 30;

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
        skip,
        limit,
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
  }, [accountId, roleId, isActive, search, skip, limit]);

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

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(skip / limit) + 1;

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
                    setSkip(0);
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
                  setSkip(0);
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
                  setSkip(0);
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
                  setSkip(0);
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
          {!loading && data && (
            <>
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Email</TableHead>
                      <TableHead>Account</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead>Last Login</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                          No users found
                        </TableCell>
                      </TableRow>
                    ) : (
                      data.map((user) => (
                        <TableRow key={user.id}>
                          <TableCell className="font-medium">{user.email}</TableCell>
                          <TableCell>
                            <div>
                              <div>{user.account_name}</div>
                              <div className="text-xs text-muted-foreground">{user.account_code}</div>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant="secondary">{user.role_name}</Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant={user.is_active ? 'default' : 'secondary'}>
                              {user.is_active ? 'Active' : 'Inactive'}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {new Date(user.created_at).toLocaleDateString()}
                          </TableCell>
                          <TableCell>
                            {user.last_login
                              ? new Date(user.last_login).toLocaleDateString()
                              : 'Never'}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-2">
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleEdit(user)}
                                title="Edit user"
                              >
                                <Pencil className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleResetPasswordClick(user)}
                                title="Reset password"
                              >
                                <Key className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleDeactivateClick(user)}
                                title="Deactivate user"
                                className="text-destructive hover:text-destructive"
                                disabled={!user.is_active}
                              >
                                <UserX className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  Showing {skip + 1}-{Math.min(skip + limit, total)} of {total} users
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => setSkip(Math.max(0, skip - limit))}
                    disabled={skip === 0}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <span className="text-sm">
                    Page {currentPage} of {totalPages || 1}
                  </span>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => setSkip(skip + limit)}
                    disabled={skip + limit >= total}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </>
          )}

          {/* Empty State */}
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
