/**
 * Roles & permissions management page
 * Full implementation with CRUD operations and permission management
 */

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Plus, RefreshCw, Shield } from 'lucide-react';
import RolesTable from '@/components/roles/RolesTable';
import CreateRoleDialog from '@/components/roles/CreateRoleDialog';
import EditRoleDialog from '@/components/roles/EditRoleDialog';
import DeleteRoleDialog from '@/components/roles/DeleteRoleDialog';
import PermissionsMatrixDialog from '@/components/roles/PermissionsMatrixDialog';
import {
    getRoles,
    createRole,
    updateRole,
    deleteRole,
    type RoleListItem,
    type RoleListResponse,
    type CreateRoleData,
    type UpdateRoleData,
} from '@/services/roles.service';
import { handleApiError } from '@/lib/api';

export default function RolesPage() {
    const [data, setData] = useState<RoleListResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Dialog state
    const [createDialogOpen, setCreateDialogOpen] = useState(false);
    const [editDialogOpen, setEditDialogOpen] = useState(false);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [permissionsDialogOpen, setPermissionsDialogOpen] = useState(false);
    const [selectedRole, setSelectedRole] = useState<RoleListItem | null>(null);

    const fetchRoles = async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await getRoles();
            setData(response);
        } catch (err) {
            setError(handleApiError(err));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRoles();
    }, []);

    const handleCreateRole = async (data: CreateRoleData) => {
        await createRole(data);
        await fetchRoles();
    };

    const handleUpdateRole = async (roleId: number, data: UpdateRoleData) => {
        await updateRole(roleId, data);
        await fetchRoles();
    };

    const handleDeleteRole = async (roleId: number) => {
        await deleteRole(roleId);
        await fetchRoles();
    };

    const handleEdit = (role: RoleListItem) => {
        setSelectedRole(role);
        setEditDialogOpen(true);
    };

    const handleDelete = (role: RoleListItem) => {
        setSelectedRole(role);
        setDeleteDialogOpen(true);
    };

    const handleViewPermissions = (role: RoleListItem) => {
        setSelectedRole(role);
        setPermissionsDialogOpen(true);
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Roles & Permissions</h1>
                    <p className="text-muted-foreground mt-2">Manage access control and permissions</p>
                </div>
                <Button onClick={() => setCreateDialogOpen(true)} className="gap-2">
                    <Plus className="h-4 w-4" />
                    Create Role
                </Button>
            </div>

            {/* Roles Management */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Shield className="h-5 w-5 text-primary" />
                        Role Management
                    </CardTitle>
                    <CardDescription>
                        Create and manage roles, configure permissions for each role
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* Refresh Button */}
                    <div className="flex justify-end">
                        <Button
                            variant="outline"
                            size="icon"
                            onClick={fetchRoles}
                            disabled={loading}
                        >
                            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                        </Button>
                    </div>

                    {/* Error State */}
                    {error && (
                        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                            <p className="text-destructive font-medium">Failed to load roles</p>
                            <p className="text-sm text-muted-foreground mt-1">{error}</p>
                            <Button onClick={fetchRoles} className="mt-4" size="sm">
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
                            <RolesTable
                                roles={data.items}
                                onEdit={handleEdit}
                                onDelete={handleDelete}
                                onViewPermissions={handleViewPermissions}
                            />

                            {/* Summary */}
                            <p className="text-sm text-muted-foreground">
                                Showing {data.items.length} role{data.items.length !== 1 ? 's' : ''}
                            </p>
                        </>
                    )}

                    {/* Empty State */}
                    {!loading && data && data.items.length === 0 && (
                        <div className="text-center py-12">
                            <Shield className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                            <h3 className="text-lg font-medium mb-2">No roles yet</h3>
                            <p className="text-muted-foreground mb-4">
                                Get started by creating your first role
                            </p>
                            <Button onClick={() => setCreateDialogOpen(true)}>
                                <Plus className="h-4 w-4 mr-2" />
                                Create Role
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Dialogs */}
            <CreateRoleDialog
                open={createDialogOpen}
                onOpenChange={setCreateDialogOpen}
                onSubmit={handleCreateRole}
            />

            <EditRoleDialog
                open={editDialogOpen}
                onOpenChange={setEditDialogOpen}
                role={selectedRole}
                onSubmit={handleUpdateRole}
            />

            <DeleteRoleDialog
                open={deleteDialogOpen}
                onOpenChange={setDeleteDialogOpen}
                role={selectedRole}
                onConfirm={handleDeleteRole}
            />

            <PermissionsMatrixDialog
                open={permissionsDialogOpen}
                onOpenChange={setPermissionsDialogOpen}
                role={selectedRole}
                onSaved={fetchRoles}
            />
        </div>
    );
}
