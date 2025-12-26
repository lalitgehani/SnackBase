/**
 * Delete group confirmation dialog
 */

import { useState } from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Loader2, AlertTriangle } from 'lucide-react';
import type { Group } from '@/services/groups.service';

interface DeleteGroupDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    group: Group | null;
    onSubmit: (groupId: string) => Promise<void>;
}

export default function DeleteGroupDialog({ open, onOpenChange, group, onSubmit }: DeleteGroupDialogProps) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async () => {
        if (!group) return;

        setLoading(true);
        setError(null);

        try {
            await onSubmit(group.id);
            onOpenChange(false);
        } catch (err: any) {
            const errorMsg = err.response?.data?.detail || err.message || 'Failed to delete group';
            setError(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5 text-destructive" />
                        Delete Group
                    </DialogTitle>
                    <DialogDescription>
                        This action cannot be undone.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <p className="text-sm">
                        Are you sure you want to delete the group <strong>{group?.name}</strong>?
                    </p>
                    <div className="bg-muted p-3 rounded-md">
                        <p className="text-sm text-muted-foreground">
                            This will remove all user associations with this group. Users will not be deleted,
                            but they will no longer be members of this group.
                        </p>
                    </div>

                    {error && (
                        <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
                            {error}
                        </div>
                    )}
                </div>

                <DialogFooter>
                    <Button
                        type="button"
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                        disabled={loading}
                    >
                        Cancel
                    </Button>
                    <Button
                        type="button"
                        variant="destructive"
                        onClick={handleSubmit}
                        disabled={loading}
                    >
                        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Delete Group
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
