/**
 * Create role dialog component
 */

import { useState } from 'react';
import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Loader2 } from 'lucide-react';

interface CreateRoleDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSubmit: (data: { name: string; description?: string }) => Promise<void>;
}

export default function CreateRoleDialog({ open, onOpenChange, onSubmit }: CreateRoleDialogProps) {
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            await onSubmit({
                name,
                description: description || undefined,
            });
            // Reset form
            setName('');
            setDescription('');
            onOpenChange(false);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Failed to create role');
        } finally {
            setLoading(false);
        }
    };

    return (
        <AppDialog
            open={open}
            onOpenChange={onOpenChange}
            title="Create Role"
            description="Create a new role. You can configure permissions for this role after creation."
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
                    <Button type="submit" form="create-role-form" disabled={loading || !name}>
                        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Create Role
                    </Button>
                </>
            }
        >
            <form id="create-role-form" onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                    <Label htmlFor="name">Name *</Label>
                    <Input
                        id="name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="editor"
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
                        placeholder="Can edit content but not publish"
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
