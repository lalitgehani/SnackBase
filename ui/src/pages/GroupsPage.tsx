/**
 * Groups management page
 * Superadmin page for managing groups within accounts
 */

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
    Plus,
    RefreshCw,
    Users as UsersIcon,
    Pencil,
    Trash2,
    UserPlus,
    Search,
    ChevronLeft,
    ChevronRight,
} from 'lucide-react';
import CreateGroupDialog from '@/components/groups/CreateGroupDialog';
import EditGroupDialog from '@/components/groups/EditGroupDialog';
import DeleteGroupDialog from '@/components/groups/DeleteGroupDialog';
import ManageGroupUsersDialog from '@/components/groups/ManageGroupUsersDialog';
import {
    getGroups,
    createGroup,
    updateGroup,
    deleteGroup,
    addUserToGroup,
    removeUserFromGroup,
    type Group,
    type GroupListParams,
    type CreateGroupRequest,
    type UpdateGroupRequest,
} from '@/services/groups.service';
import { handleApiError } from '@/lib/api';

export default function GroupsPage() {
    const [data, setData] = useState<Group[] | null>(null);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Filters
    const [search, setSearch] = useState('');

    // Pagination
    const [skip, setSkip] = useState(0);
    const limit = 30;

    // Dialog state
    const [createDialogOpen, setCreateDialogOpen] = useState(false);
    const [editDialogOpen, setEditDialogOpen] = useState(false);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [manageUsersDialogOpen, setManageUsersDialogOpen] = useState(false);
    const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);

    const fetchGroups = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const params: GroupListParams = {
                skip,
                limit,
            };

            if (search) params.search = search;

            const response = await getGroups(params);
            setData(response.items);
            setTotal(response.total);
        } catch (err) {
            setError(handleApiError(err));
        } finally {
            setLoading(false);
        }
    }, [search, skip, limit]);

    useEffect(() => {
        fetchGroups();
    }, [fetchGroups]);

    const handleCreateGroup = async (data: CreateGroupRequest) => {
        await createGroup(data);
        await fetchGroups();
    };

    const handleUpdateGroup = async (groupId: string, data: UpdateGroupRequest) => {
        await updateGroup(groupId, data);
        await fetchGroups();
    };

    const handleDeleteGroup = async (groupId: string) => {
        await deleteGroup(groupId);
        await fetchGroups();
    };

    const handleAddUserToGroup = async (groupId: string, userId: string) => {
        await addUserToGroup(groupId, userId);
    };

    const handleRemoveUserFromGroup = async (groupId: string, userId: string) => {
        await removeUserFromGroup(groupId, userId);
    };

    const handleEdit = (group: Group) => {
        setSelectedGroup(group);
        setEditDialogOpen(true);
    };

    const handleDelete = (group: Group) => {
        setSelectedGroup(group);
        setDeleteDialogOpen(true);
    };

    const handleManageUsers = (group: Group) => {
        setSelectedGroup(group);
        setManageUsersDialogOpen(true);
    };

    const totalPages = Math.ceil(total / limit);
    const currentPage = Math.floor(skip / limit) + 1;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Groups</h1>
                    <p className="text-muted-foreground mt-2">Manage groups for organizing users and permissions</p>
                </div>
                <Button onClick={() => setCreateDialogOpen(true)} className="gap-2">
                    <Plus className="h-4 w-4" />
                    Create Group
                </Button>
            </div>

            {/* Groups Management */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <UsersIcon className="h-5 w-5 text-primary" />
                        Group Management
                    </CardTitle>
                    <CardDescription>
                        Create and manage groups to organize users and control access
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
                                    placeholder="Search by name..."
                                    value={search}
                                    onChange={(e) => {
                                        setSearch(e.target.value);
                                        setSkip(0);
                                    }}
                                    className="pl-8 w-64"
                                />
                            </div>
                        </div>

                        <div className="ml-auto">
                            <Button variant="outline" size="icon" onClick={fetchGroups} disabled={loading}>
                                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                            </Button>
                        </div>
                    </div>

                    {/* Error State */}
                    {error && (
                        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                            <p className="text-destructive font-medium">Failed to load groups</p>
                            <p className="text-sm text-muted-foreground mt-1">{error}</p>
                            <Button onClick={fetchGroups} className="mt-4" size="sm">
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
                                            <TableHead>Name</TableHead>
                                            <TableHead>Description</TableHead>
                                            <TableHead>Account</TableHead>
                                            <TableHead>Created</TableHead>
                                            <TableHead className="text-right">Actions</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {data.length === 0 ? (
                                            <TableRow>
                                                <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                                                    No groups found
                                                </TableCell>
                                            </TableRow>
                                        ) : (
                                            data.map((group) => (
                                                <TableRow key={group.id}>
                                                    <TableCell className="font-medium">{group.name}</TableCell>
                                                    <TableCell>
                                                        <span className="text-sm text-muted-foreground">
                                                            {group.description || '—'}
                                                        </span>
                                                    </TableCell>
                                                    <TableCell>
                                                        <span className="text-xs text-muted-foreground">{group.account_id}</span>
                                                    </TableCell>
                                                    <TableCell>
                                                        {new Date(group.created_at).toLocaleDateString()}
                                                    </TableCell>
                                                    <TableCell className="text-right">
                                                        <div className="flex justify-end gap-2">
                                                            <Button
                                                                variant="ghost"
                                                                size="icon"
                                                                onClick={() => handleManageUsers(group)}
                                                                title="Manage users"
                                                            >
                                                                <UserPlus className="h-4 w-4" />
                                                            </Button>
                                                            <Button
                                                                variant="ghost"
                                                                size="icon"
                                                                onClick={() => handleEdit(group)}
                                                                title="Edit group"
                                                            >
                                                                <Pencil className="h-4 w-4" />
                                                            </Button>
                                                            <Button
                                                                variant="ghost"
                                                                size="icon"
                                                                onClick={() => handleDelete(group)}
                                                                title="Delete group"
                                                                className="text-destructive hover:text-destructive"
                                                            >
                                                                <Trash2 className="h-4 w-4" />
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
                                    Showing {skip + 1}-{Math.min(skip + limit, total)} of {total} groups
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
                            <h3 className="text-lg font-medium mb-2">No groups found</h3>
                            <p className="text-muted-foreground mb-4">
                                {search
                                    ? 'Try adjusting your search'
                                    : 'Get started by creating your first group'}
                            </p>
                            <Button onClick={() => setCreateDialogOpen(true)}>
                                <Plus className="h-4 w-4 mr-2" />
                                Create Group
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Dialogs */}
            <CreateGroupDialog
                open={createDialogOpen}
                onOpenChange={setCreateDialogOpen}
                onSubmit={handleCreateGroup}
            />

            <EditGroupDialog
                open={editDialogOpen}
                onOpenChange={setEditDialogOpen}
                group={selectedGroup}
                onSubmit={handleUpdateGroup}
            />

            <DeleteGroupDialog
                open={deleteDialogOpen}
                onOpenChange={setDeleteDialogOpen}
                group={selectedGroup}
                onSubmit={handleDeleteGroup}
            />

            <ManageGroupUsersDialog
                open={manageUsersDialogOpen}
                onOpenChange={setManageUsersDialogOpen}
                group={selectedGroup}
                onAddUser={handleAddUserToGroup}
                onRemoveUser={handleRemoveUserFromGroup}
            />
        </div>
    );
}
