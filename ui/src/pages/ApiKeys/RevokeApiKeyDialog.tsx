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
import { apiKeysService } from '@/services/api-keys.service';
import type { APIKeyListItem } from '@/services/api-keys.service';
import { useToast } from '@/hooks/use-toast';
import { useState } from 'react';

interface RevokeApiKeyDialogProps {
    apiKey: APIKeyListItem | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onRevoked: () => void;
}

export const RevokeApiKeyDialog = ({
    apiKey,
    open,
    onOpenChange,
    onRevoked,
}: RevokeApiKeyDialogProps) => {
    const [isRevoking, setIsRevoking] = useState(false);
    const { toast } = useToast();

    const handleRevoke = async () => {
        if (!apiKey) return;

        setIsRevoking(true);
        try {
            await apiKeysService.revokeApiKey(apiKey.id);
            toast({
                title: 'API key revoked',
                description: `Key "${apiKey.name}" has been successfully revoked.`,
            });
            onRevoked();
            onOpenChange(false);
        } catch (error: any) {
            toast({
                title: 'Error revoking API key',
                description: error.response?.data?.detail || 'Something went wrong',
                variant: 'destructive',
            });
        } finally {
            setIsRevoking(false);
        }
    };

    return (
        <AlertDialog open={open} onOpenChange={onOpenChange}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                    <AlertDialogDescription>
                        This will permanently revoke the API key <strong>"{apiKey?.name}"</strong>.
                        Any applications or scripts using this key will immediately lose access.
                        This action cannot be undone.
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                    <AlertDialogCancel disabled={isRevoking}>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                        className="bg-red-600 hover:bg-red-700 focus:ring-red-600"
                        onClick={handleRevoke}
                        disabled={isRevoking}
                    >
                        {isRevoking ? 'Revoking...' : 'Revoke Key'}
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
};
