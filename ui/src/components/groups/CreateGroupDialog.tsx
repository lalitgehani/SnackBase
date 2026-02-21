/**
 * Create group dialog component
 */

import { useEffect, useState } from 'react';
import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Loader2 } from 'lucide-react';
import type { CreateGroupRequest } from '@/services/groups.service';
import { getAccounts, type Account } from '@/services/accounts.service';

interface CreateGroupDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSubmit: (data: CreateGroupRequest) => Promise<void>;
}

export default function CreateGroupDialog({ open, onOpenChange, onSubmit }: CreateGroupDialogProps) {
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [accountId, setAccountId] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [accounts, setAccounts] = useState<Account[]>([]);
    const [loadingAccounts, setLoadingAccounts] = useState(false);

    // Load accounts when dialog opens
    useEffect(() => {
        if (open) {
            loadAccounts();
        }
    }, [open]);

    const loadAccounts = async () => {
        setLoadingAccounts(true);
        try {
            const response = await getAccounts({ page_size: 100 });
            setAccounts(response.items);
        } catch (err) {
            console.error('Failed to load accounts:', err);
        } finally {
            setLoadingAccounts(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            await onSubmit({
                name,
                description: description || null,
                account_id: accountId || undefined,
            });
            // Reset form
            setName('');
            setDescription('');
            setAccountId('');
            onOpenChange(false);
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string | unknown } }; message?: string };
            const errorMsg = error.response?.data?.detail || error.message || 'Failed to create group';
            setError(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
        } finally {
            setLoading(false);
        }
    };

    const isFormValid = name.trim().length > 0 && accountId;

    return (
        <AppDialog
            open={open}
            onOpenChange={onOpenChange}
            title="Create Group"
            description="Create a new group to organize users and manage permissions."
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
                    <Button type="submit" form="create-group-form" disabled={loading || !isFormValid || loadingAccounts}>
                        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Create Group
                    </Button>
                </>
            }
        >
            {loadingAccounts ? (
                <div className="flex justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
            ) : (
                <form id="create-group-form" onSubmit={handleSubmit} className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="account">Account *</Label>
                        <Select
                            value={accountId}
                            onValueChange={setAccountId}
                            disabled={loading}
                        >
                            <SelectTrigger id="account">
                                <SelectValue placeholder="Select an account" />
                            </SelectTrigger>
                            <SelectContent>
                                {accounts.map((account) => (
                                    <SelectItem key={account.id} value={account.id}>
                                        {account.name} ({account.id})
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="name">Name *</Label>
                        <Input
                            id="name"
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
                        <Label htmlFor="description">Description</Label>
                        <Textarea
                            id="description"
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
                </form>
            )}
        </AppDialog>
    );
}
