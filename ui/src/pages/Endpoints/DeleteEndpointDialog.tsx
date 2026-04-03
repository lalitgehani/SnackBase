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
import { endpointsService, type Endpoint } from '@/services/endpoints.service';
import { useToast } from '@/hooks/use-toast';

interface Props {
    endpoint: Endpoint;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onDeleted: () => void;
}

export function DeleteEndpointDialog({ endpoint, open, onOpenChange, onDeleted }: Props) {
    const { toast } = useToast();
    const [loading, setLoading] = useState(false);

    const handleDelete = async () => {
        setLoading(true);
        try {
            await endpointsService.delete(endpoint.id);
            toast({ title: 'Endpoint deleted' });
            onDeleted();
            onOpenChange(false);
        } catch {
            toast({ title: 'Error', description: 'Failed to delete endpoint', variant: 'destructive' });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[420px]">
                <DialogHeader>
                    <DialogTitle>Delete Endpoint</DialogTitle>
                    <DialogDescription>
                        Are you sure you want to delete{' '}
                        <span className="font-medium text-foreground">{endpoint.name}</span>? This
                        action cannot be undone.
                    </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                    <Button
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                        disabled={loading}
                    >
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
