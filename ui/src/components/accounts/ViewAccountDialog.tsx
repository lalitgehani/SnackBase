/**
 * View account dialog component
 * Displays account details in read-only mode
 */

import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import type { AccountListItem } from '@/services/accounts.service';

interface ViewAccountDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    account: AccountListItem | null;
}

export default function ViewAccountDialog({
    open,
    onOpenChange,
    account,
}: ViewAccountDialogProps) {
    if (!account) return null;

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleString();
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle>Account Details</DialogTitle>
                    <DialogDescription>
                        Detailed information for account {account.account_code}
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1">
                            <Label className="text-muted-foreground text-xs uppercase">Account Code</Label>
                            <div className="font-mono font-medium">{account.account_code}</div>
                        </div>
                        <div className="space-y-1">
                            <Label className="text-muted-foreground text-xs uppercase">Status</Label>
                            <div>
                                <Badge variant="default">{account.status}</Badge>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-1">
                        <Label className="text-muted-foreground text-xs uppercase">Name</Label>
                        <div className="text-base font-semibold">{account.name}</div>
                    </div>

                    <div className="space-y-1">
                        <Label className="text-muted-foreground text-xs uppercase">Slug</Label>
                        <div className="text-sm">{account.slug}</div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1">
                            <Label className="text-muted-foreground text-xs uppercase">User Count</Label>
                            <div className="text-sm font-medium">{account.user_count}</div>
                        </div>
                        <div className="space-y-1">
                            <Label className="text-muted-foreground text-xs uppercase">Created At</Label>
                            <div className="text-sm">{formatDate(account.created_at)}</div>
                        </div>
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>
                        Close
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
