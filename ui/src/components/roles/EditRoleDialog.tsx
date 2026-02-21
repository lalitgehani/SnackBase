/**
 * Edit role dialog component
 */

import { useState, useEffect } from 'react';
import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Loader2 } from 'lucide-react';
import type { RoleListItem } from '@/services/roles.service';

interface EditRoleDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    role: RoleListItem | null;
    onSubmit: (roleId: number, data: { name: string; description?: string }) => Promise<void>;
}

export default function EditRoleDialog({ open, onOpenChange, role, onSubmit }: EditRoleDialogProps) {
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (role) {
            setName(role.name);
            setDescription(role.description || '');
        }
    }, [role]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!role) return;

        setLoading(true);
        setError(null);

        try {
            await onSubmit(role.id, {
                name,
                description: description || undefined,
            });
            onOpenChange(false);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Failed to update role');
        } finally {
            setLoading(false);
        }
    };

    if (!role) return null;

    return (
        <AppDialog
            open={open}
            onOpenChange={onOpenChange}
            title="Edit Role"
            description="Update the role name and description."
            footer={
                <>
                    <Button
                        type="button"
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                        disabled={loading}
                    >
                        Cancel
                    </Button>
                    <Button type="submit" form="edit-role-form" disabled={loading || !name}>
                        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Save Changes
                    </Button>
                </>
            }
        >
            <form id="edit-role-form" onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                    <Label htmlFor="name">Name *</Label>
                    <Input
                        id="name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        required
                        disabled={loading}
                    />
                </div>

                <div className="space-y-2">
                    <Label htmlFor="description">Description (optional)</Label>
                    <Textarea
                        id="description"
                        value={description}
                        onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDescription(e.target.value)}
                        rows={3}
                        disabled={loading}
                    />
                </div>

                {error && (
                    <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
                        {error}
                    </div>
                )}
            </form>
        </AppDialog>
    );
}
