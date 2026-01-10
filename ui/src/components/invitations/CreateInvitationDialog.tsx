
import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { Button } from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { createInvitation, type InvitationCreateRequest } from '@/services/invitations.service';
import { getAccounts, type AccountListItem } from '@/services/accounts.service';
import { handleApiError } from '@/lib/api';
import { useToast } from "@/hooks/use-toast";

interface CreateInvitationDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSuccess: () => void;
}

export function CreateInvitationDialog({
    open,
    onOpenChange,
    onSuccess,
}: CreateInvitationDialogProps) {
    const { toast } = useToast();
    const [isLoading, setIsLoading] = useState(false);
    const [accounts, setAccounts] = useState<AccountListItem[]>([]);
    const [loadingAccounts, setLoadingAccounts] = useState(false);
    const [showAccountSelect, setShowAccountSelect] = useState(false);
    const { register, handleSubmit, reset, getValues, formState: { errors } } = useForm<InvitationCreateRequest>();

    useEffect(() => {
        const loadAccounts = async () => {
            try {
                setLoadingAccounts(true);
                const response = await getAccounts({ page_size: 100 });
                if (response.items && response.items.length > 0) {
                    setAccounts(response.items);
                    setShowAccountSelect(true);
                }
            } catch (error) {
                // Ignore error - likely not superadmin, so just don't show account selector
                console.debug("Failed to load accounts for invitation selector", error);
            } finally {
                setLoadingAccounts(false);
            }
        };
        loadAccounts();
    }, []);

    const onSubmit = async (data: InvitationCreateRequest) => {
        setIsLoading(true);
        try {
            await createInvitation(data);
            toast({
                title: "Invitation sent",
                description: `Invitation sent to ${data.email}`,
            });
            reset();
            onSuccess();
            onOpenChange(false);
        } catch (err) {
            toast({
                variant: "destructive",
                title: "Error",
                description: handleApiError(err),
            });
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Invite User</DialogTitle>
                    <DialogDescription>
                        Send an invitation email to a new user. They will receive a link to set their password.
                    </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-4">
                    <div className="space-y-2">
                        <Label htmlFor="email">Email address</Label>
                        <Input
                            id="email"
                            type="email"
                            placeholder="user@example.com"
                            disabled={isLoading}
                            {...register('email', {
                                required: 'Email is required',
                                pattern: {
                                    value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                                    message: "Invalid email address"
                                }
                            })}
                        />
                        {errors.email && (
                            <p className="text-sm text-destructive">{errors.email.message}</p>
                        )}
                    </div>

                    {showAccountSelect && (
                        <div className="space-y-2">
                            <Label htmlFor="account">Account (Optional)</Label>
                            <Select
                                onValueChange={(value) => reset({ ...getValues(), account_id: value })}
                                disabled={isLoading || loadingAccounts}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="Select an account" />
                                </SelectTrigger>
                                <SelectContent>
                                    {accounts.map((account) => (
                                        <SelectItem key={account.id} value={account.id}>
                                            {account.name} ({account.account_code})
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <p className="text-xs text-muted-foreground">Leave empty to invite to your current account.</p>
                        </div>
                    )}
                    <DialogFooter>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => onOpenChange(false)}
                            disabled={isLoading}
                        >
                            Cancel
                        </Button>
                        <Button type="submit" disabled={isLoading}>
                            {isLoading ? 'Sending...' : 'Send Invitation'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
