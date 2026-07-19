import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import type { WorkflowTriggerConfig } from '@/services/workflows.service';
import { WORKFLOW_EVENTS } from '../../workflowConstants';

interface Props {
    trigger: WorkflowTriggerConfig;
    onChange: (trigger: WorkflowTriggerConfig) => void;
}

type TriggerType = WorkflowTriggerConfig['type'];

export function TriggerProperties({ trigger, onChange }: Props) {
    const type: TriggerType = trigger.type;

    const setType = (t: TriggerType) => {
        switch (t) {
            case 'event':
                onChange({
                    type: 'event',
                    event: 'records.create',
                });
                break;
            case 'schedule':
                onChange({ type: 'schedule', cron: '0 9 * * *' });
                break;
            case 'webhook':
                onChange({ type: 'webhook' });
                break;
            default:
                onChange({ type: 'manual' });
        }
    };

    return (
        <div className="space-y-3" data-testid="properties-trigger">
            <div className="space-y-1.5">
                <Label className="text-xs">Trigger type</Label>
                <Select value={type} onValueChange={(v) => setType(v as TriggerType)}>
                    <SelectTrigger className="h-8 text-sm" data-testid="properties-trigger-type">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="manual">Manual</SelectItem>
                        <SelectItem value="event">Event</SelectItem>
                        <SelectItem value="schedule">Schedule</SelectItem>
                        <SelectItem value="webhook">Webhook</SelectItem>
                    </SelectContent>
                </Select>
            </div>

            {type === 'event' && trigger.type === 'event' && (
                <>
                    <div className="space-y-1.5">
                        <Label className="text-xs">Event</Label>
                        <Select
                            value={trigger.event}
                            onValueChange={(v) => onChange({ ...trigger, event: v })}
                        >
                            <SelectTrigger className="h-8 text-sm">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {WORKFLOW_EVENTS.map((ev) => (
                                    <SelectItem key={ev.value} value={ev.value}>
                                        {ev.label}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-1.5">
                        <Label className="text-xs">Collection (optional)</Label>
                        <Input
                            className="h-8 text-sm"
                            value={trigger.collection ?? ''}
                            onChange={(e) =>
                                onChange({
                                    ...trigger,
                                    collection: e.target.value || undefined,
                                })
                            }
                            placeholder="e.g. posts"
                        />
                    </div>
                    <div className="space-y-1.5">
                        <Label className="text-xs">Condition (optional)</Label>
                        <Input
                            className="h-8 text-sm font-mono"
                            value={trigger.condition ?? ''}
                            onChange={(e) =>
                                onChange({
                                    ...trigger,
                                    condition: e.target.value || undefined,
                                })
                            }
                            placeholder='status == "active"'
                        />
                    </div>
                </>
            )}

            {type === 'schedule' && trigger.type === 'schedule' && (
                <div className="space-y-1.5">
                    <Label className="text-xs">Cron expression</Label>
                    <Input
                        className="h-8 text-sm font-mono"
                        value={trigger.cron}
                        onChange={(e) => onChange({ type: 'schedule', cron: e.target.value })}
                        placeholder="0 9 * * *"
                    />
                    <p className="text-[10px] text-muted-foreground">Standard 5-field cron</p>
                </div>
            )}

            {type === 'webhook' && (
                <p className="text-xs text-muted-foreground">
                    Webhook URL and token are available after save from the workflow details.
                </p>
            )}

            {type === 'manual' && (
                <p className="text-xs text-muted-foreground">
                    Run this workflow manually from the list or API.
                </p>
            )}
        </div>
    );
}
