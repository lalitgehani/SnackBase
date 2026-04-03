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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { CronInput } from '@/components/CronInput';
import { scheduledTasksService, type ScheduledTask } from '@/services/scheduledTasks.service';
import { useToast } from '@/hooks/use-toast';

interface Props {
    task: ScheduledTask;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onUpdated: () => void;
}


export function EditScheduledTaskDialog({ task, open, onOpenChange, onUpdated }: Props) {
    const { toast } = useToast();
    const [loading, setLoading] = useState(false);
    const [form, setForm] = useState({
        name: task.name,
        description: task.description ?? '',
        cron: task.cron ?? '',
        enabled: task.enabled,
    });

    useEffect(() => {
        setForm({
            name: task.name,
            description: task.description ?? '',
            cron: task.cron ?? '',
            enabled: task.enabled,
        });
    }, [task]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.name.trim() || !form.cron.trim()) return;

        setLoading(true);
        try {
            await scheduledTasksService.update(task.id, {
                name: form.name.trim(),
                description: form.description.trim() || undefined,
                cron: form.cron.trim(),
                enabled: form.enabled,
            });
            toast({ title: 'Scheduled task updated' });
            onUpdated();
            onOpenChange(false);
        } catch (err: unknown) {
            const msg =
                (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
                'Failed to update task';
            toast({ title: 'Error', description: msg, variant: 'destructive' });
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[500px]">
                <form onSubmit={handleSubmit}>
                    <DialogHeader>
                        <DialogTitle>Edit Scheduled Task</DialogTitle>
                        <DialogDescription>Update the task configuration.</DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4 py-4">
                        <div className="space-y-1.5">
                            <Label htmlFor="edit-name">Name</Label>
                            <Input
                                id="edit-name"
                                value={form.name}
                                onChange={(e) => setForm({ ...form, name: e.target.value })}
                                required
                            />
                        </div>

                        <div className="space-y-1.5">
                            <Label htmlFor="edit-description">Description (optional)</Label>
                            <Textarea
                                id="edit-description"
                                rows={2}
                                value={form.description}
                                onChange={(e) => setForm({ ...form, description: e.target.value })}
                            />
                        </div>

                        <CronInput
                            id="edit-cron"
                            value={form.cron}
                            onChange={(v) => setForm({ ...form, cron: v })}
                            required
                        />

                        <div className="flex items-center gap-3">
                            <Switch
                                id="edit-enabled"
                                checked={form.enabled}
                                onCheckedChange={(v) => setForm({ ...form, enabled: v })}
                            />
                            <Label htmlFor="edit-enabled">Enabled</Label>
                        </div>
                    </div>

                    <DialogFooter>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => onOpenChange(false)}
                            disabled={loading}
                        >
                            Cancel
                        </Button>
                        <Button type="submit" disabled={loading || !form.name.trim() || !form.cron.trim()}>
                            {loading ? 'Saving…' : 'Save Changes'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
