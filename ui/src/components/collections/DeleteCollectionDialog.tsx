/**
 * Delete collection dialog component
 * Shows confirmation with record count warning
 */

import { useState } from 'react';
import {
    AlertDialog,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { CheckCircle2, Loader2 } from 'lucide-react';
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
    const [isSuccess, setIsSuccess] = useState(false);
    const [deletedCollectionName, setDeletedCollectionName] = useState('');

    const handleConfirm = async () => {
        if (!collection || confirmText !== collection.name) return;

        setIsDeleting(true);
        try {
            await onConfirm(collection.id);
            setDeletedCollectionName(collection.name);
            setIsSuccess(true);
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
                setIsSuccess(false);
                setDeletedCollectionName('');
            }
        }
    };

    const handleClose = () => {
        onOpenChange(false);
        setIsSuccess(false);
        setDeletedCollectionName('');
        setConfirmText('');
    };

    if (!collection) return null;

    const isConfirmValid = confirmText === collection.name;

    return (
        <AlertDialog open={open} onOpenChange={handleOpenChange}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>
                        {isSuccess ? 'Collection Deleted' : 'Delete Collection'}
                    </AlertDialogTitle>
                    <AlertDialogDescription asChild>
                        <div>
                            {isDeleting && (
                                <div className="flex flex-col items-center justify-center py-8 space-y-4">
                                    <Loader2 className="h-12 w-12 animate-spin text-destructive" />
                                    <div className="text-center">
                                        <p className="font-medium">Deleting collection and applying migrations...</p>
                                        <p className="text-sm text-muted-foreground mt-1">
                                            Please wait while the database table is being dropped.
                                        </p>
                                    </div>
                                </div>
                            )}

                            {isSuccess && !isDeleting && (
                                <div className="flex flex-col items-center justify-center py-8 space-y-4">
                                    <div className="rounded-full bg-green-100 dark:bg-green-900/30 p-4">
                                        <CheckCircle2 className="h-12 w-12 text-green-600 dark:text-green-400" />
                                    </div>
                                    <div className="text-center space-y-2">
                                        <p className="font-medium text-lg">
                                            Collection "{deletedCollectionName}" deleted successfully!
                                        </p>
                                        <p className="text-sm text-muted-foreground">
                                            The database table has been dropped and all migrations are complete.
                                        </p>
                                    </div>
                                </div>
                            )}

                            {!isSuccess && !isDeleting && (
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
                            )}
                        </div>
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                    {isSuccess ? (
                        <Button onClick={handleClose}>Done</Button>
                    ) : (
                        <>
                            <Button
                                variant="outline"
                                onClick={() => onOpenChange(false)}
                                disabled={isDeleting}
                            >
                                Cancel
                            </Button>
                            <Button
                                variant="destructive"
                                onClick={handleConfirm}
                                disabled={!isConfirmValid || isDeleting}
                            >
                                {isDeleting ? 'Deleting...' : 'Delete Collection'}
                            </Button>
                        </>
                    )}
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}
