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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Field, FieldLabel, FieldContent } from '@/components/ui/field';
import { Checkbox } from '@/components/ui/checkbox';
import { apiKeysService } from '@/services/api-keys.service';
import type { APIKeyCreateResponse } from '@/services/api-keys.service';
import { useToast } from '@/hooks/use-toast';
import { CopyToClipboardButton } from './CopyToClipboardButton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Info, AlertTriangle } from 'lucide-react';

interface CreateApiKeyDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onCreated: () => void;
}

export const CreateApiKeyDialog = ({
    open,
    onOpenChange,
    onCreated,
}: CreateApiKeyDialogProps) => {
    const [name, setName] = useState('');
    const [neverExpires, setNeverExpires] = useState(true);
    const [expiresAt, setExpiresAt] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [createdKey, setCreatedKey] = useState<APIKeyCreateResponse | null>(null);
    const { toast } = useToast();

    const handleCreate = async () => {
        if (!name) return;

        setIsSubmitting(true);
        try {
            const response = await apiKeysService.createApiKey({
                name,
                expires_at: neverExpires ? null : expiresAt,
            });
            setCreatedKey(response);
            onCreated();
        } catch (error: any) {
            toast({
                title: 'Error creating API key',
                description: error.response?.data?.detail || 'Something went wrong',
                variant: 'destructive',
            });
        } finally {
            setIsSubmitting(false);
        }
    };

    const resetAndClose = () => {
        setName('');
        setNeverExpires(true);
        setExpiresAt('');
        setCreatedKey(null);
        onOpenChange(false);
    };

    if (createdKey) {
        return (
            <Dialog open={open} onOpenChange={resetAndClose}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>API Key Created</DialogTitle>
                        <DialogDescription>
                            Copy your API key now. You won't be able to see it again!
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4 py-4">
                        <Alert variant="destructive" className="bg-amber-50 border-amber-200 text-amber-900">
                            <AlertTriangle className="h-4 w-4 text-amber-600" />
                            <AlertTitle>Important Security Warning</AlertTitle>
                            <AlertDescription>
                                This key provides full superadmin access. Store it securely and never share it.
                            </AlertDescription>
                        </Alert>

                        <div className="flex items-center space-x-2 bg-slate-100 p-3 rounded border font-mono text-sm break-all">
                            <span className="flex-1 select-all">{createdKey.key}</span>
                            <CopyToClipboardButton value={createdKey.key} label="API Key" />
                        </div>
                    </div>

                    <DialogFooter>
                        <Button onClick={resetAndClose}>I've saved my key</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        );
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>Create API Key</DialogTitle>
                    <DialogDescription>
                        Generate a persistent key for programmatic superadmin access.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <Field>
                        <FieldLabel>Key Name <span className="text-destructive">*</span></FieldLabel>
                        <FieldContent>
                            <Input
                                placeholder="e.g. CI/CD Deployment Key"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                            />
                        </FieldContent>
                    </Field>

                    <div className="flex items-center space-x-2">
                        <Checkbox
                            id="never-expires"
                            checked={neverExpires}
                            onCheckedChange={(checked) => setNeverExpires(checked === true)}
                        />
                        <Label htmlFor="never-expires">Never expires</Label>
                    </div>

                    {!neverExpires && (
                        <Field>
                            <FieldLabel>Expiration Date</FieldLabel>
                            <FieldContent>
                                <Input
                                    type="datetime-local"
                                    value={expiresAt}
                                    onChange={(e) => setExpiresAt(e.target.value)}
                                />
                            </FieldContent>
                        </Field>
                    )}

                    <Alert variant="default" className="bg-blue-50 border-blue-200 text-blue-900">
                        <Info className="h-4 w-4 text-blue-600" />
                        <AlertDescription>
                            API keys allow bypassing JWT authentication for automated tasks.
                        </AlertDescription>
                    </Alert>
                </div>

                <DialogFooter>
                    <Button variant="ghost" onClick={() => onOpenChange(false)}>
                        Cancel
                    </Button>
                    <Button onClick={handleCreate} disabled={!name || isSubmitting}>
                        {isSubmitting ? 'Creating...' : 'Create Key'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};
