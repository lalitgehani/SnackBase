import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { endpointsService } from '@/services/endpoints.service';
import { useToast } from '@/hooks/use-toast';
import { EndpointFormFields, DEFAULT_FORM, formToPayload, type EndpointFormState } from './EndpointFormFields';

interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onCreated: () => void;
    accountSlug?: string;
}

export function CreateEndpointDialog({ open, onOpenChange, onCreated, accountSlug }: Props) {
    const { toast } = useToast();
    const [loading, setLoading] = useState(false);
    const [form, setForm] = useState<EndpointFormState>(DEFAULT_FORM);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.name.trim() || !form.path.trim()) return;

        setLoading(true);
        try {
            await endpointsService.create(formToPayload(form));
            toast({ title: 'Endpoint created' });
            onCreated();
            onOpenChange(false);
            setForm(DEFAULT_FORM);
        } catch (err: unknown) {
            const msg =
                (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
                'Failed to create endpoint';
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
                        <DialogTitle>Create Endpoint</DialogTitle>
                        <DialogDescription>
                            Define a serverless HTTP endpoint that runs actions and returns a response.
                        </DialogDescription>
                    </DialogHeader>

                    <EndpointFormFields
                        form={form}
                        setForm={setForm}
                        accountSlug={accountSlug}
                        idPrefix="create-"
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
                            {loading ? 'Creating…' : 'Create Endpoint'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
