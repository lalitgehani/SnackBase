import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { endpointsService, type Endpoint } from '@/services/endpoints.service';
import { useToast } from '@/hooks/use-toast';
import { EndpointFormFields, endpointToForm, formToPayload, type EndpointFormState } from './EndpointFormFields';

interface Props {
    endpoint: Endpoint;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onUpdated: () => void;
    accountSlug?: string;
}

export function EditEndpointDialog({ endpoint, open, onOpenChange, onUpdated, accountSlug }: Props) {
    const { toast } = useToast();
    const [loading, setLoading] = useState(false);
    const [form, setForm] = useState<EndpointFormState>(() => endpointToForm(endpoint));

    useEffect(() => {
        setForm(endpointToForm(endpoint));
    }, [endpoint]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.name.trim() || !form.path.trim()) return;

        setLoading(true);
        try {
            await endpointsService.update(endpoint.id, formToPayload(form));
            toast({ title: 'Endpoint updated' });
            onUpdated();
            onOpenChange(false);
        } catch (err: unknown) {
            const msg =
                (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
                'Failed to update endpoint';
            toast({ title: 'Error', description: msg, variant: 'destructive' });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[620px] max-h-[90vh] overflow-y-auto">
                <form onSubmit={handleSubmit}>
                    <DialogHeader>
                        <DialogTitle>Edit Endpoint</DialogTitle>
                        <DialogDescription>Update the endpoint configuration.</DialogDescription>
                    </DialogHeader>

                    <EndpointFormFields
                        form={form}
                        setForm={setForm}
                        accountSlug={accountSlug}
                        idPrefix="edit-"
                    />

                    <DialogFooter>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => onOpenChange(false)}
                            disabled={loading}
                        >
                            Cancel
                        </Button>
                        <Button type="submit" disabled={loading || !form.name.trim() || !form.path.trim()}>
                            {loading ? 'Saving…' : 'Save Changes'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
