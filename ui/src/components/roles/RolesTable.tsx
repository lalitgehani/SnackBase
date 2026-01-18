/**
 * Roles table component
 * Displays list of roles with actions
 */

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Pencil, Trash2 } from 'lucide-react';
import type { RoleListItem } from '@/services/roles.service';

interface RolesTableProps {
    roles: RoleListItem[];
    onEdit: (role: RoleListItem) => void;
    onDelete: (role: RoleListItem) => void;
}

const DEFAULT_ROLES = ['admin', 'user'];

export default function RolesTable({ roles, onEdit, onDelete }: RolesTableProps) {
    const isDefaultRole = (roleName: string) => DEFAULT_ROLES.includes(roleName.toLowerCase());

    return (
        <div className="rounded-md border">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Description</TableHead>
                        <TableHead>Collections</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {roles.length === 0 ? (
                        <TableRow>
                            <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                                No roles found
                            </TableCell>
                        </TableRow>
                    ) : (
                        roles.map((role) => (
                            <TableRow key={role.id}>
                                <TableCell className="font-medium">
                                    <div className="flex items-center gap-2">
                                        {role.name}
                                        {isDefaultRole(role.name) && (
                                            <Badge variant="secondary" className="text-xs">
                                                Default
                                            </Badge>
                                        )}
                                    </div>
                                </TableCell>
                                <TableCell className="text-muted-foreground">
                                    {role.description || '-'}
                                </TableCell>
                                <TableCell>{role.collections_count}</TableCell>
                                <TableCell className="text-right">
                                    <div className="flex justify-end gap-2">
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            onClick={() => onEdit(role)}
                                            title="Edit role"
                                        >
                                            <Pencil className="h-4 w-4" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            onClick={() => onDelete(role)}
                                            title="Delete role"
                                            className="text-destructive hover:text-destructive"
                                            disabled={isDefaultRole(role.name)}
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
    );
}
