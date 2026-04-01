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
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from '@/components/ui/popover';
import { Button as PopoverButton } from '@/components/ui/button';
import { Lightbulb } from 'lucide-react';
import { scheduledTasksService, type CreateScheduledTaskRequest } from '@/services/scheduledTasks.service';
import { useToast } from '@/hooks/use-toast';

interface Props {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onCreated: () => void;
}

const CRON_PRESETS = [
    { label: 'Every minute', value: '* * * * *' },
    { label: 'Every 5 minutes', value: '*/5 * * * *' },
    { label: 'Every 15 minutes', value: '*/15 * * * *' },
    { label: 'Every 30 minutes', value: '*/30 * * * *' },
    { label: 'Every hour', value: '0 * * * *' },
    { label: 'Daily at midnight', value: '0 0 * * *' },
    { label: 'Daily at 9am', value: '0 9 * * *' },
    { label: 'Weekdays at 9am', value: '0 9 * * 1-5' },
    { label: 'Every Monday at 9am', value: '0 9 * * 1' },
    { label: 'Monthly on the 1st', value: '0 0 1 * *' },
];

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

                        <div className="space-y-1.5">
                            <div className="flex items-center justify-between">
                                <Label htmlFor="cron">Cron Expression</Label>
                                <Popover>
                                    <PopoverTrigger asChild>
                                        <PopoverButton
                                            type="button"
                                            variant="ghost"
                                            size="sm"
                                            className="h-7 gap-1 text-xs text-muted-foreground"
                                        >
                                            <Lightbulb className="h-3.5 w-3.5" />
                                            Presets
                                        </PopoverButton>
                                    </PopoverTrigger>
                                    <PopoverContent className="w-56 p-1" align="end">
                                        <div className="space-y-0.5">
                                            {CRON_PRESETS.map((preset) => (
                                                <button
                                                    key={preset.value}
                                                    type="button"
                                                    className="w-full rounded px-2 py-1.5 text-left text-sm hover:bg-muted"
                                                    onClick={() =>
                                                        setForm({ ...form, cron: preset.value })
                                                    }
                                                >
                                                    <span className="font-medium">{preset.label}</span>
                                                    <span className="ml-2 font-mono text-xs text-muted-foreground">
                                                        {preset.value}
                                                    </span>
                                                </button>
                                            ))}
                                        </div>
                                    </PopoverContent>
                                </Popover>
                            </div>
                            <Input
                                id="cron"
                                placeholder="0 9 * * MON"
                                className="font-mono"
                                value={form.cron}
                                onChange={(e) => setForm({ ...form, cron: e.target.value })}
                                required
                            />
                            <p className="text-xs text-muted-foreground">
                                Format: minute hour day month weekday (e.g. <code>0 9 * * 1-5</code> = weekdays at 9am)
                            </p>
                        </div>

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
