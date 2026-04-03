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
import { hooksService } from '@/services/hooks.service';
import { useToast } from '@/hooks/use-toast';
import { HookFormFields, DEFAULT_FORM, formToPayload, type HookFormState } from './HookFormFields';

interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onCreated: () => void;
}

export function CreateHookDialog({ open, onOpenChange, onCreated }: Props) {
    const { toast } = useToast();
    const [loading, setLoading] = useState(false);
    const [form, setForm] = useState<HookFormState>(DEFAULT_FORM);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.name.trim()) return;

        setLoading(true);
        try {
            await hooksService.create(formToPayload(form));
            toast({ title: 'Hook created' });
            onCreated();
            onOpenChange(false);
            setForm(DEFAULT_FORM);
        } catch (err: unknown) {
            const msg =
                (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
                'Failed to create hook';
            toast({ title: 'Error', description: msg, variant: 'destructive' });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
                <form onSubmit={handleSubmit}>
                    <DialogHeader>
                        <DialogTitle>Create Hook</DialogTitle>
                        <DialogDescription>
                            Define event-driven or manual business logic that executes actions.
                        </DialogDescription>
                    </DialogHeader>

                    <HookFormFields form={form} setForm={setForm} idPrefix="create-" />

                    <DialogFooter>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => onOpenChange(false)}
                            disabled={loading}
                        >
                            Cancel
                        </Button>
                        <Button type="submit" disabled={loading || !form.name.trim()}>
                            {loading ? 'Creating…' : 'Create Hook'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
