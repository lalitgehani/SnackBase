import { useEffect, useState } from 'react';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { workflowsService, type Workflow } from '@/services/workflows.service';
import { useToast } from '@/hooks/use-toast';
import type { WorkflowFormState } from './WorkflowFormFields';
import { WorkflowFormFields, DEFAULT_FORM, formToPayload, workflowToForm } from './WorkflowFormFields';

interface Props {
    workflow: Workflow;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onUpdated: () => void;
}

export function EditWorkflowDialog({ workflow, open, onOpenChange, onUpdated }: Props) {
    const { toast } = useToast();
    const [form, setForm] = useState<WorkflowFormState>(DEFAULT_FORM);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (open) {
            setForm(workflowToForm(workflow));
        }
    }, [open, workflow]);

    const handleSubmit = async () => {
        if (!form.name.trim()) {
            toast({ title: 'Name is required', variant: 'destructive' });
            return;
        }

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
            await workflowsService.update(workflow.id, formToPayload(form));
            toast({ title: 'Workflow updated' });
            onOpenChange(false);
            onUpdated();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Failed to update workflow';
            toast({ title: 'Error', description: msg, variant: 'destructive' });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Edit Workflow</DialogTitle>
                </DialogHeader>

                <WorkflowFormFields form={form} setForm={setForm} />

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
                        Cancel
                    </Button>
                    <Button onClick={handleSubmit} disabled={loading}>
                        {loading ? 'Saving…' : 'Save Changes'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
