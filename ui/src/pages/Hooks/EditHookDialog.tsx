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
import { hooksService, type Hook } from '@/services/hooks.service';
import { useToast } from '@/hooks/use-toast';
import { HookFormFields, hookToForm, formToPayload, type HookFormState } from './HookFormFields';

interface Props {
    hook: Hook;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onUpdated: () => void;
}

export function EditHookDialog({ hook, open, onOpenChange, onUpdated }: Props) {
    const { toast } = useToast();
    const [loading, setLoading] = useState(false);
    const [form, setForm] = useState<HookFormState>(() => hookToForm(hook));

    useEffect(() => {
        setForm(hookToForm(hook));
    }, [hook]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.name.trim()) return;

        setLoading(true);
        try {
            await hooksService.update(hook.id, formToPayload(form));
            toast({ title: 'Hook updated' });
            onUpdated();
            onOpenChange(false);
        } catch (err: unknown) {
            const msg =
                (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
                'Failed to update hook';
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
                        <DialogTitle>Edit Hook</DialogTitle>
                        <DialogDescription>Update the hook configuration.</DialogDescription>
                    </DialogHeader>

                    <HookFormFields form={form} setForm={setForm} idPrefix="edit-" />

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
                            {loading ? 'Saving…' : 'Save Changes'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
