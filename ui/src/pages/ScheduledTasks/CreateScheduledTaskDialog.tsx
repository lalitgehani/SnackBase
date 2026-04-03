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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { CronInput } from '@/components/CronInput';
import { scheduledTasksService, type CreateScheduledTaskRequest } from '@/services/scheduledTasks.service';
import { useToast } from '@/hooks/use-toast';

interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onCreated: () => void;
}


export function CreateScheduledTaskDialog({ open, onOpenChange, onCreated }: Props) {
    const { toast } = useToast();
    const [loading, setLoading] = useState(false);
    const [form, setForm] = useState<CreateScheduledTaskRequest & { enabled: boolean }>({
        name: '',
        description: '',
        cron: '',
        enabled: true,
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.name.trim() || !form.cron.trim()) return;

        setLoading(true);
        try {
            await scheduledTasksService.create({
                name: form.name.trim(),
                description: form.description?.trim() || undefined,
                cron: form.cron.trim(),
                enabled: form.enabled,
            });
            toast({ title: 'Scheduled task created' });
            onCreated();
            onOpenChange(false);
            setForm({ name: '', description: '', cron: '', enabled: true });
        } catch (err: unknown) {
            const msg =
                (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
                'Failed to create task';
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
                        <DialogTitle>Create Scheduled Task</DialogTitle>
                        <DialogDescription>
                            Define a recurring task using a cron expression.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4 py-4">
                        <div className="space-y-1.5">
                            <Label htmlFor="name">Name</Label>
                            <Input
                                id="name"
                                placeholder="e.g. Daily report"
                                value={form.name}
                                onChange={(e) => setForm({ ...form, name: e.target.value })}
                                required
                            />
                        </div>

                        <div className="space-y-1.5">
                            <Label htmlFor="description">Description (optional)</Label>
                            <Textarea
                                id="description"
                                placeholder="What does this task do?"
                                rows={2}
                                value={form.description}
                                onChange={(e) => setForm({ ...form, description: e.target.value })}
                            />
                        </div>

                        <CronInput
                            id="cron"
                            value={form.cron}
                            onChange={(v) => setForm({ ...form, cron: v })}
                            required
                        />

                        <div className="flex items-center gap-3">
                            <Switch
                                id="enabled"
                                checked={form.enabled}
                                onCheckedChange={(v) => setForm({ ...form, enabled: v })}
                            />
                            <Label htmlFor="enabled">Enable immediately</Label>
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
                            {loading ? 'Creating…' : 'Create Task'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
