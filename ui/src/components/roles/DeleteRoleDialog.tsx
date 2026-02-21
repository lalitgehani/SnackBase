/**
 * Delete role dialog component
 */

import { useState } from 'react';
import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { Loader2, AlertTriangle } from 'lucide-react';
import type { RoleListItem } from '@/services/roles.service';

interface DeleteRoleDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    role: RoleListItem | null;
    onConfirm: (roleId: number) => Promise<void>;
}

const DEFAULT_ROLES = ['admin', 'user'];

export default function DeleteRoleDialog({
    open,
    onOpenChange,
    role,
    onConfirm,
}: DeleteRoleDialogProps) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const isDefaultRole = role && DEFAULT_ROLES.includes(role.name.toLowerCase());

    const handleConfirm = async () => {
        if (!role) return;

        setLoading(true);
        setError(null);

        try {
            await onConfirm(role.id);
            onOpenChange(false);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Failed to delete role');
        } finally {
            setLoading(false);
        }
    };

    if (!role) return null;

    return (
        <AppDialog
            open={open}
            onOpenChange={onOpenChange}
            title="Delete Role"
            description={
                isDefaultRole
                    ? 'This is a default role and cannot be deleted.'
                    : 'Are you sure you want to delete this role?'
            }
            footer={
                <>
                    <Button
                        type="button"
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                        disabled={loading}
                    >
                        {isDefaultRole ? 'Close' : 'Cancel'}
                    </Button>
                    {!isDefaultRole && (
                        <Button
                            variant="destructive"
                            onClick={handleConfirm}
                            disabled={loading}
                        >
                            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Delete Role
                        </Button>
                    )}
                </>
            }
        >
            <div className="space-y-4">
                {!isDefaultRole && (
                    <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                        <div className="flex gap-3">
                            <AlertTriangle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
                            <div className="space-y-2">
                                <p className="font-medium text-destructive">Warning</p>
                                <p className="text-sm text-muted-foreground">
                                    Deleting role <span className="font-medium">{role.name}</span> will:
                                </p>
                                <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
                                    <li>Remove all permissions associated with this role</li>
                                    <li>Affect users currently assigned to this role</li>
                                </ul>
                                <p className="text-sm font-medium text-destructive">
                                    This action cannot be undone.
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                {isDefaultRole && (
                    <div className="bg-muted/50 border rounded-lg p-4">
                        <p className="text-sm text-muted-foreground">
                            Default roles (admin, user) are required for the system to function properly
                            and cannot be deleted.
                        </p>
                    </div>
                )}

                {error && (
                    <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
                        {error}
                    </div>
                )}
            </div>
        </AppDialog>
    );
}
