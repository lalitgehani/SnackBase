/**
 * Create account dialog component
 */

import { useState } from 'react';
import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2 } from 'lucide-react';

interface CreateAccountDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSubmit: (data: { name: string; slug?: string }) => Promise<void>;
}

export default function CreateAccountDialog({
    open,
    onOpenChange,
    onSubmit,
}: CreateAccountDialogProps) {
    const [name, setName] = useState('');
    const [slug, setSlug] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            await onSubmit({
                name,
                slug: slug || undefined,
            });
            // Reset form
            setName('');
            setSlug('');
            onOpenChange(false);
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } }; message?: string };
            setError(error.response?.data?.detail || error.message || 'Failed to create account');
        } finally {
            setLoading(false);
        }
    };

    return (
        <AppDialog
            open={open}
            onOpenChange={onOpenChange}
            title="Create Account"
            description="Create a new tenant account. The account ID will be generated automatically."
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
                    <Button type="submit" form="create-account-form" disabled={loading || !name}>
                        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Create Account
                    </Button>
                </>
            }
        >
            <form id="create-account-form" onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                    <Label htmlFor="name">Name *</Label>
                    <Input
                        id="name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="My Company"
                        required
                        disabled={loading}
                    />
                </div>

                <div className="space-y-2">
                    <Label htmlFor="slug">Slug (optional)</Label>
                    <Input
                        id="slug"
                        value={slug}
                        onChange={(e) => setSlug(e.target.value)}
                        placeholder="my-company"
                        pattern="[a-z0-9-]+"
                        disabled={loading}
                    />
                    <p className="text-xs text-muted-foreground">
                        Leave empty to auto-generate from name. Only lowercase letters, numbers, and hyphens.
                    </p>
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
