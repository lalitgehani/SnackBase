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
import { webhooksService, type WebhookListItem } from '@/services/webhooks.service';
import { useToast } from '@/hooks/use-toast';

interface DeleteWebhookDialogProps {
    webhook: WebhookListItem | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onDeleted: () => void;
}

export function DeleteWebhookDialog({
    webhook,
    open,
    onOpenChange,
    onDeleted,
}: DeleteWebhookDialogProps) {
    const [isDeleting, setIsDeleting] = useState(false);
    const { toast } = useToast();

    const handleDelete = async () => {
        if (!webhook) return;
        setIsDeleting(true);
        try {
            await webhooksService.delete(webhook.id);
            toast({ title: 'Webhook deleted' });
            onDeleted();
            onOpenChange(false);
        } catch (error: any) {
            toast({
                title: 'Error deleting webhook',
                description: error.response?.data?.detail || 'Something went wrong',
                variant: 'destructive',
            });
        } finally {
            setIsDeleting(false);
        }
    };

    return (
        <AlertDialog open={open} onOpenChange={onOpenChange}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>Delete webhook?</AlertDialogTitle>
                    <AlertDialogDescription>
                        This will permanently delete the webhook targeting{' '}
                        <strong className="break-all">{webhook?.url}</strong> and all its delivery history.
                        This action cannot be undone.
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                    <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                        className="bg-red-600 hover:bg-red-700 focus:ring-red-600"
                        onClick={handleDelete}
                        disabled={isDeleting}
                    >
                        {isDeleting ? 'Deleting...' : 'Delete Webhook'}
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}
