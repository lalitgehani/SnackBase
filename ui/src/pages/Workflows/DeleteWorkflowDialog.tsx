import { useState } from 'react';
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

interface Props {
    workflow: Workflow;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onDeleted: () => void;
}

export function DeleteWorkflowDialog({ workflow, open, onOpenChange, onDeleted }: Props) {
    const { toast } = useToast();
    const [loading, setLoading] = useState(false);

    const handleDelete = async () => {
        setLoading(true);
        try {
            await workflowsService.delete(workflow.id);
            toast({ title: 'Workflow deleted' });
            onOpenChange(false);
            onDeleted();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Failed to delete workflow';
            toast({ title: 'Error', description: msg, variant: 'destructive' });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[440px]">
                <DialogHeader>
                    <DialogTitle>Delete Workflow</DialogTitle>
                </DialogHeader>
                <div className="space-y-2 text-sm text-muted-foreground">
                    <p>
                        Are you sure you want to delete <strong className="text-foreground">{workflow.name}</strong>?
                    </p>
                    <p>
                        All running and waiting instances will be cancelled. This action cannot be undone.
                    </p>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
                        Cancel
                    </Button>
                    <Button variant="destructive" onClick={handleDelete} disabled={loading}>
                        {loading ? 'Deleting…' : 'Delete'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
