/**
 * Edit group dialog component
 */

import { useEffect, useState } from 'react';
import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Loader2 } from 'lucide-react';
import type { Group, UpdateGroupRequest } from '@/services/groups.service';

interface EditGroupDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    group: Group | null;
    onSubmit: (groupId: string, data: UpdateGroupRequest) => Promise<void>;
}

export default function EditGroupDialog({ open, onOpenChange, group, onSubmit }: EditGroupDialogProps) {
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Populate form when group changes
    useEffect(() => {
        if (group) {
            setName(group.name);
            setDescription(group.description || '');
        }
    }, [group]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!group) return;

        setLoading(true);
        setError(null);

        try {
            await onSubmit(group.id, {
                name,
                description: description || null,
            });
            onOpenChange(false);
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string | unknown } }; message?: string };
            const errorMsg = error.response?.data?.detail || error.message || 'Failed to update group';
            setError(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
        } finally {
            setLoading(false);
        }
    };

    const isFormValid = name.trim().length > 0;

    return (
        <AppDialog
            open={open}
            onOpenChange={onOpenChange}
            title="Edit Group"
            description="Update the group name and description."
            className="max-w-md"
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
                    <Button type="submit" form="edit-group-form" disabled={loading || !isFormValid}>
                        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Save Changes
                    </Button>
                </>
            }
        >
            <form id="edit-group-form" onSubmit={handleSubmit}>
                <div className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="edit-name">Name *</Label>
                        <Input
                            id="edit-name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="e.g., Managers, Developers"
                            required
                            disabled={loading}
                            maxLength={100}
                        />
                        <p className="text-xs text-muted-foreground">
                            1-100 characters
                        </p>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="edit-description">Description</Label>
                        <Textarea
                            id="edit-description"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="Optional description of the group's purpose"
                            disabled={loading}
                            maxLength={500}
                            rows={3}
                        />
                        <p className="text-xs text-muted-foreground">
                            Optional, max 500 characters
                        </p>
                    </div>

                    {error && (
                        <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
                            {error}
                        </div>
                    )}
                </div>
            </form>
        </AppDialog>
    );
}
