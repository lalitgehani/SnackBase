/**
 * Delete macro dialog component
 */

import { useState } from 'react';
import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { Loader2, AlertTriangle } from 'lucide-react';
import type { Macro } from '@/types/macro';

interface DeleteMacroDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    macro: Macro | null;
    onConfirm: (macroId: number) => Promise<void>;
}

export default function DeleteMacroDialog({
    open,
    onOpenChange,
    macro,
    onConfirm,
}: DeleteMacroDialogProps) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleConfirm = async () => {
        if (!macro) return;

        setLoading(true);
        setError(null);

        try {
            await onConfirm(macro.id);
            onOpenChange(false);
        } catch (err: unknown) {
            const error = err as { response?: { data?: { detail?: string } }; message?: string };
            setError(error.response?.data?.detail || error.message || 'Failed to delete macro');
        } finally {
            setLoading(false);
        }
    };

    if (!macro) return null;

    return (
        <AppDialog
            open={open}
            onOpenChange={onOpenChange}
            title="Delete Macro"
            description="Are you sure you want to delete this macro?"
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
                    <Button
                        variant="destructive"
                        onClick={handleConfirm}
                        disabled={loading}
                    >
                        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Delete Macro
                    </Button>
                </>
            }
        >
            <div className="space-y-4">
                <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                    <div className="flex gap-3">
                        <AlertTriangle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
                        <div className="space-y-2">
                            <p className="font-medium text-destructive">Warning</p>
                            <p className="text-sm text-muted-foreground">
                                Deleting macro <span className="font-medium">@{macro.name}</span> will:
                            </p>
                            <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
                                <li>Remove this SQL snippet from your macro library</li>
                                <li>Break any permission rules that reference @{macro.name}</li>
                                <li>Potentially cause authorization errors in your application</li>
                            </ul>
                            <p className="text-sm font-medium text-destructive">
                                This action cannot be undone.
                            </p>
                        </div>
                    </div>
                </div>

                {error && (
                    <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
                        {error}
                    </div>
                )}
            </div>
        </AppDialog>
    );
}
