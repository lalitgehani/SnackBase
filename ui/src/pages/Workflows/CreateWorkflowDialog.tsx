import { useState } from 'react';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { workflowsService } from '@/services/workflows.service';
import { useToast } from '@/hooks/use-toast';
import type { WorkflowFormState } from './WorkflowFormFields';
import { WorkflowFormFields, DEFAULT_FORM, formToPayload } from './WorkflowFormFields';

interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onCreated: () => void;
}

export function CreateWorkflowDialog({ open, onOpenChange, onCreated }: Props) {
    const { toast } = useToast();
    const [form, setForm] = useState<WorkflowFormState>(DEFAULT_FORM);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async () => {
        if (!form.name.trim()) {
            toast({ title: 'Name is required', variant: 'destructive' });
            return;
        }

        // Validate step names are unique and non-empty
        const names = form.steps.map((s) => s.name.trim());
        if (names.some((n) => !n)) {
            toast({ title: 'All steps must have a name', variant: 'destructive' });
            return;
        }
        if (new Set(names).size !== names.length) {
            toast({ title: 'Step names must be unique', variant: 'destructive' });
            return;
        }

        setLoading(true);
        try {
            await workflowsService.create(formToPayload(form));
            toast({ title: 'Workflow created' });
            setForm(DEFAULT_FORM);
            onOpenChange(false);
            onCreated();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Failed to create workflow';
            toast({ title: 'Error', description: msg, variant: 'destructive' });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>New Workflow</DialogTitle>
                </DialogHeader>

                <WorkflowFormFields form={form} setForm={setForm} />

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
                        Cancel
                    </Button>
                    <Button onClick={handleSubmit} disabled={loading}>
                        {loading ? 'Creating…' : 'Create Workflow'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
