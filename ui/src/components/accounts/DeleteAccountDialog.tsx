/**
 * Delete account confirmation dialog
 */

import { useState } from 'react';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2, AlertTriangle } from 'lucide-react';
import type { AccountListItem } from '@/services/accounts.service';

interface DeleteAccountDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    account: AccountListItem | null;
    onConfirm: (accountId: string) => Promise<void>;
}

export default function DeleteAccountDialog({
    open,
    onOpenChange,
    account,
    onConfirm,
}: DeleteAccountDialogProps) {
    const [confirmName, setConfirmName] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleConfirm = async () => {
        if (!account) return;

        setLoading(true);
        setError(null);

        try {
            await onConfirm(account.id);
            setConfirmName('');
            onOpenChange(false);
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } }; message?: string };
            setError(error.response?.data?.detail || error.message || 'Failed to delete account');
        } finally {
            setLoading(false);
        }
    };

    const handleOpenChange = (open: boolean) => {
        if (!loading) {
            setConfirmName('');
            setError(null);
            onOpenChange(open);
        }
    };

    if (!account) return null;

    const isConfirmValid = confirmName === account.name;

    return (
        <AlertDialog open={open} onOpenChange={handleOpenChange}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle className="flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5 text-destructive" />
                        Delete Account
                    </AlertDialogTitle>
                    <AlertDialogDescription className="space-y-3">
                        <p>
                            You are about to delete account <strong>{account.name}</strong> ({account.account_code}).
                        </p>
                        <div className="bg-destructive/10 border border-destructive/20 rounded-md p-3">
                            <p className="text-sm font-medium text-destructive">
                                ⚠️ Warning: This action cannot be undone!
                            </p>
                            <ul className="text-sm text-destructive mt-2 space-y-1 list-disc list-inside">
                                <li>All {account.user_count} user(s) will be deleted</li>
                                <li>All associated data will be permanently removed</li>
                                <li>Collections and records will be deleted</li>
                            </ul>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="confirm-name">
                                Type <strong>{account.name}</strong> to confirm:
                            </Label>
                            <Input
                                id="confirm-name"
                                value={confirmName}
                                onChange={(e) => setConfirmName(e.target.value)}
                                placeholder={account.name}
                                disabled={loading}
                            />
                        </div>
                        {error && (
                            <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
                                {error}
                            </div>
                        )}
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                    <AlertDialogCancel disabled={loading}>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                        onClick={handleConfirm}
                        disabled={!isConfirmValid || loading}
                        className="bg-destructive text-white hover:bg-destructive/90"
                    >
                        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Delete Account
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}
