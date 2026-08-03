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
import { functionsService, type FunctionItem } from '@/services/functions.service';
import { useToast } from '@/hooks/use-toast';

interface Props {
  functionItem: FunctionItem | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeleted: () => void;
}

export function DeleteFunctionDialog({ functionItem, open, onOpenChange, onDeleted }: Props) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);

  const handleDelete = async () => {
    if (!functionItem) return;
    setLoading(true);
    try {
      await functionsService.delete(functionItem.slug);
      toast({ title: 'Function removed' });
      onDeleted();
      onOpenChange(false);
    } catch {
      toast({ title: 'Error', description: 'Failed to delete function', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete function</DialogTitle>
          <DialogDescription>
            Soft-delete <strong>{functionItem?.name}</strong> ({functionItem?.slug}). Invokes will
            return 404. Execution history is retained.
          </DialogDescription>
        </DialogHeader>
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
