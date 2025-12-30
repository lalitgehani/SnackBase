/**
 * Accounts management page
 * Full implementation with CRUD operations, search, and pagination
 */

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Users, Plus, Search, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react';
import AccountsTable from '@/components/accounts/AccountsTable';
import CreateAccountDialog from '@/components/accounts/CreateAccountDialog';
import ViewAccountDialog from '@/components/accounts/ViewAccountDialog';
import EditAccountDialog from '@/components/accounts/EditAccountDialog';
import DeleteAccountDialog from '@/components/accounts/DeleteAccountDialog';
import {
    getAccounts,
    createAccount,
    updateAccount,
    deleteAccount,
    type AccountListItem,
    type AccountListResponse,
    type CreateAccountData,
    type UpdateAccountData,
} from '@/services/accounts.service';
import { handleApiError } from '@/lib/api';

export default function AccountsPage() {
    const [data, setData] = useState<AccountListResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Pagination and filtering state
    const [page, setPage] = useState(1);
    const [pageSize] = useState(25);
    const [sortBy, setSortBy] = useState('created_at');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
    const [search, setSearch] = useState('');
    const [searchInput, setSearchInput] = useState('');

    // Dialog state
    const [createDialogOpen, setCreateDialogOpen] = useState(false);
    const [viewDialogOpen, setViewDialogOpen] = useState(false);
    const [editDialogOpen, setEditDialogOpen] = useState(false);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [selectedAccount, setSelectedAccount] = useState<AccountListItem | null>(null);

    const fetchAccounts = async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await getAccounts({
                page,
                page_size: pageSize,
                sort_by: sortBy,
                sort_order: sortOrder,
                search: search || undefined,
            });
            setData(response);
        } catch (err) {
            setError(handleApiError(err));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAccounts();
    }, [page, sortBy, sortOrder, search]);

    const handleSort = (column: string) => {
        if (sortBy === column) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortBy(column);
            setSortOrder('desc');
        }
    };

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        setSearch(searchInput);
        setPage(1);
    };

    const handleCreateAccount = async (data: CreateAccountData) => {
        await createAccount(data);
        await fetchAccounts();
    };

    const handleUpdateAccount = async (accountId: string, data: UpdateAccountData) => {
        await updateAccount(accountId, data);
        await fetchAccounts();
    };

    const handleDeleteAccount = async (accountId: string) => {
        await deleteAccount(accountId);
        await fetchAccounts();
    };

    const handleView = (account: AccountListItem) => {
        setSelectedAccount(account);
        setViewDialogOpen(true);
    };

    const handleEdit = (account: AccountListItem) => {
        setSelectedAccount(account);
        setEditDialogOpen(true);
    };

    const handleDelete = (account: AccountListItem) => {
        setSelectedAccount(account);
        setDeleteDialogOpen(true);
    };

    const totalPages = data?.total_pages || 1;
    const canGoPrevious = page > 1;
    const canGoNext = page < totalPages;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Accounts</h1>
                    <p className="text-muted-foreground mt-2">Manage tenant accounts</p>
                </div>
                <Button onClick={() => setCreateDialogOpen(true)} className="gap-2">
                    <Plus className="h-4 w-4" />
                    Create Account
                </Button>
            </div>

            {/* Search and Actions */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Users className="h-5 w-5 text-primary" />
                        Account Management
                    </CardTitle>
                    <CardDescription>
                        View, create, edit, and delete tenant accounts
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* Search Bar */}
                    <form onSubmit={handleSearch} className="flex gap-2">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                                value={searchInput}
                                onChange={(e) => setSearchInput(e.target.value)}
                                placeholder="Search by name, slug, or code..."
                                className="pl-9"
                            />
                        </div>
                        <Button type="submit" variant="secondary">
                            Search
                        </Button>
                        {search && (
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => {
                                    setSearch('');
                                    setSearchInput('');
                                    setPage(1);
                                }}
                            >
                                Clear
                            </Button>
                        )}
                        <Button
                            type="button"
                            variant="outline"
                            size="icon"
                            onClick={fetchAccounts}
                            disabled={loading}
                        >
                            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                        </Button>
                    </form>

                    {/* Error State */}
                    {error && (
                        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                            <p className="text-destructive font-medium">Failed to load accounts</p>
                            <p className="text-sm text-muted-foreground mt-1">{error}</p>
                            <Button onClick={fetchAccounts} className="mt-4" size="sm">
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
                            <AccountsTable
                                accounts={data.items}
                                sortBy={sortBy}
                                sortOrder={sortOrder}
                                onSort={handleSort}
                                onView={handleView}
                                onEdit={handleEdit}
                                onDelete={handleDelete}
                            />

                            {/* Pagination */}
                            <div className="flex items-center justify-between">
                                <p className="text-sm text-muted-foreground">
                                    Showing {data.items.length === 0 ? 0 : (page - 1) * pageSize + 1} to{' '}
                                    {Math.min(page * pageSize, data.total)} of {data.total} accounts
                                </p>
                                <div className="flex items-center gap-2">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => setPage(page - 1)}
                                        disabled={!canGoPrevious}
                                    >
                                        <ChevronLeft className="h-4 w-4 mr-1" />
                                        Previous
                                    </Button>
                                    <span className="text-sm">
                                        Page {page} of {totalPages}
                                    </span>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => setPage(page + 1)}
                                        disabled={!canGoNext}
                                    >
                                        Next
                                        <ChevronRight className="h-4 w-4 ml-1" />
                                    </Button>
                                </div>
                            </div>
                        </>
                    )}

                    {/* Empty State */}
                    {!loading && data && data.items.length === 0 && !search && (
                        <div className="text-center py-12">
                            <Users className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                            <h3 className="text-lg font-medium mb-2">No accounts yet</h3>
                            <p className="text-muted-foreground mb-4">
                                Get started by creating your first account
                            </p>
                            <Button onClick={() => setCreateDialogOpen(true)}>
                                <Plus className="h-4 w-4 mr-2" />
                                Create Account
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Dialogs */}
            <CreateAccountDialog
                open={createDialogOpen}
                onOpenChange={setCreateDialogOpen}
                onSubmit={handleCreateAccount}
            />

            <ViewAccountDialog
                open={viewDialogOpen}
                onOpenChange={setViewDialogOpen}
                account={selectedAccount}
            />

            <EditAccountDialog
                open={editDialogOpen}
                onOpenChange={setEditDialogOpen}
                account={selectedAccount}
                onSubmit={handleUpdateAccount}
            />

            <DeleteAccountDialog
                open={deleteDialogOpen}
                onOpenChange={setDeleteDialogOpen}
                account={selectedAccount}
                onConfirm={handleDeleteAccount}
            />
        </div>
    );
}
