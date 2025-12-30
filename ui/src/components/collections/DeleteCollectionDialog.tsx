/**
 * Delete collection dialog component
 * Shows confirmation with record count warning
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
import type { CollectionListItem } from '@/services/collections.service';

interface DeleteCollectionDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    collection: CollectionListItem | null;
    onConfirm: (collectionId: string) => Promise<void>;
}

export default function DeleteCollectionDialog({
    open,
    onOpenChange,
    collection,
    onConfirm,
}: DeleteCollectionDialogProps) {
    const [confirmText, setConfirmText] = useState('');
    const [isDeleting, setIsDeleting] = useState(false);

    const handleConfirm = async () => {
        if (!collection || confirmText !== collection.name) return;

        setIsDeleting(true);
        try {
            await onConfirm(collection.id);
            onOpenChange(false);
            setConfirmText('');
        } catch (error) {
            console.error('Failed to delete collection:', error);
        } finally {
            setIsDeleting(false);
        }
    };

    const handleOpenChange = (newOpen: boolean) => {
        if (!isDeleting) {
            onOpenChange(newOpen);
            if (!newOpen) {
                setConfirmText('');
            }
        }
    };

    if (!collection) return null;

    const isConfirmValid = confirmText === collection.name;

    return (
        <AlertDialog open={open} onOpenChange={handleOpenChange}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>Delete Collection</AlertDialogTitle>
                    <AlertDialogDescription asChild>
                        <div className="space-y-4">
                            <p>
                                Are you sure you want to delete the collection <strong>{collection.name}</strong>?
                            </p>

                            {collection.records_count > 0 && (
                                <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                                    <p className="text-destructive font-medium">
                                        ⚠️ Warning: This collection contains {collection.records_count} record
                                        {collection.records_count !== 1 ? 's' : ''}
                                    </p>
                                    <p className="text-sm text-muted-foreground mt-2">
                                        All data will be permanently deleted and cannot be recovered.
                                    </p>
                                </div>
                            )}

                            <div className="bg-muted/50 rounded-lg p-4 space-y-2 text-sm">
                                <p className="font-medium">This action will:</p>
                                <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                                    <li>Drop the physical database table</li>
                                    <li>Delete all {collection.records_count} records</li>
                                    <li>Remove the collection definition</li>
                                    <li>Cannot be undone</li>
                                </ul>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="confirm-name">
                                    Type <strong>{collection.name}</strong> to confirm
                                </Label>
                                <Input
                                    id="confirm-name"
                                    value={confirmText}
                                    onChange={(e) => setConfirmText(e.target.value)}
                                    placeholder={collection.name}
                                    disabled={isDeleting}
                                />
                            </div>
                        </div>
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                    <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                        onClick={handleConfirm}
                        disabled={!isConfirmValid || isDeleting}
                        className="bg-destructive text-white hover:bg-destructive/90"
                    >
                        {isDeleting ? 'Deleting...' : 'Delete Collection'}
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}
