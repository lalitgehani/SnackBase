import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import type { WorkflowStep } from '@/services/workflows.service';
import { WORKFLOW_EVENTS } from '../../workflowConstants';
import { StepNameField } from './StepNameField';

interface Props {
    step: WorkflowStep;
    onChange: (step: WorkflowStep) => void;
    onRename: (name: string) => void;
}

export function WaitProperties({ step, onChange, onRename }: Props) {
    return (
        <div className="space-y-3" data-testid={`properties-${step.type}`}>
            <StepNameField name={step.name} onRename={onRename} />

            {step.type === 'wait_delay' && (
                <div className="space-y-1.5">
                    <Label htmlFor="prop-wait-duration" className="text-xs">
                        Duration
                    </Label>
                    <Input
                        id="prop-wait-duration"
                        className="h-8 text-sm"
                        value={String(step.duration ?? '')}
                        onChange={(e) => onChange({ ...step, duration: e.target.value })}
                        placeholder="5m, 2h, 1d"
                    />
                    <p className="text-[10px] text-muted-foreground">Supports: Ns, Nm, Nh, Nd</p>
                </div>
            )}

            {step.type === 'wait_condition' && (
                <>
                    <div className="space-y-1.5">
                        <Label htmlFor="prop-wait-expression" className="text-xs">
                            Expression
                        </Label>
                        <Input
                            id="prop-wait-expression"
                            className="h-8 text-sm font-mono"
                            value={String(step.expression ?? '')}
                            onChange={(e) => onChange({ ...step, expression: e.target.value })}
                            placeholder='record.status == "approved"'
                        />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="prop-wait-poll" className="text-xs">
                            Poll interval
                        </Label>
                        <Input
                            id="prop-wait-poll"
                            className="h-8 text-sm"
                            value={String(step.poll_interval ?? '')}
                            onChange={(e) => onChange({ ...step, poll_interval: e.target.value })}
                            placeholder="1m"
                        />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="prop-wait-timeout" className="text-xs">
                            Timeout
                        </Label>
                        <Input
                            id="prop-wait-timeout"
                            className="h-8 text-sm"
                            value={String(step.timeout ?? '')}
                            onChange={(e) => onChange({ ...step, timeout: e.target.value })}
                            placeholder="24h"
                        />
                    </div>
                </>
            )}

            {step.type === 'wait_event' && (
                <>
                    <div className="space-y-1.5">
                        <Label htmlFor="prop-wait-event" className="text-xs">
                            Event
                        </Label>
                        <Select
                            value={String(step.event ?? 'records.create')}
                            onValueChange={(v) => onChange({ ...step, event: v })}
                        >
                            <SelectTrigger id="prop-wait-event" className="h-8 text-sm">
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
                        <Label htmlFor="prop-wait-collection" className="text-xs">
                            Collection (optional)
                        </Label>
                        <Input
                            id="prop-wait-collection"
                            className="h-8 text-sm"
                            value={String(step.collection ?? '')}
                            onChange={(e) =>
                                onChange({
                                    ...step,
                                    collection: e.target.value || undefined,
                                })
                            }
                        />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="prop-wait-event-timeout" className="text-xs">
                            Timeout
                        </Label>
                        <Input
                            id="prop-wait-event-timeout"
                            className="h-8 text-sm"
                            value={String(step.timeout ?? '')}
                            onChange={(e) => onChange({ ...step, timeout: e.target.value })}
                            placeholder="24h"
                        />
                    </div>
                </>
            )}
        </div>
    );
}
