/**
 * Shared form fields for CreateWorkflowDialog and EditWorkflowDialog.
 */
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Plus, X } from 'lucide-react';
import type { Workflow, WorkflowTriggerConfig, WorkflowStep } from '@/services/workflows.service';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const WORKFLOW_EVENTS = [
    { value: 'records.create', label: 'records.create — Record created' },
    { value: 'records.update', label: 'records.update — Record updated' },
    { value: 'records.delete', label: 'records.delete — Record deleted' },
    { value: 'auth.login', label: 'auth.login — User logged in' },
    { value: 'auth.register', label: 'auth.register — User registered' },
] as const;

export const STEP_TYPES = [
    { value: 'action', label: 'Action' },
    { value: 'condition', label: 'Condition (branch)' },
    { value: 'wait_delay', label: 'Wait — Delay' },
    { value: 'wait_condition', label: 'Wait — Until Condition' },
    { value: 'wait_event', label: 'Wait — For Event' },
    { value: 'loop', label: 'Loop' },
    { value: 'parallel', label: 'Parallel' },
] as const;

export const ACTION_TYPES = [
    { value: 'send_webhook', label: 'Send Webhook' },
    { value: 'send_email', label: 'Send Email' },
    { value: 'create_record', label: 'Create Record' },
    { value: 'update_record', label: 'Update Record' },
    { value: 'delete_record', label: 'Delete Record' },
    { value: 'enqueue_job', label: 'Enqueue Job' },
] as const;

// ---------------------------------------------------------------------------
// Form state types
// ---------------------------------------------------------------------------

export interface StepFormItem {
    name: string;
    type: string;
    next: string;
    // action
    action_type: string;
    config: string; // JSON
    // condition
    expression: string;
    on_true: string;
    on_false: string;
    // wait_delay
    duration: string;
    // wait_condition
    poll_interval: string;
    timeout: string;
    // wait_event
    event: string;
    collection: string;
    // loop
    items: string;
    step: string;
    // parallel
    branches: string; // JSON array of arrays
}

export interface WorkflowFormState {
    name: string;
    description: string;
    triggerType: 'event' | 'schedule' | 'manual' | 'webhook';
    triggerEvent: string;
    triggerCollection: string;
    triggerCondition: string;
    triggerCron: string;
    steps: StepFormItem[];
    enabled: boolean;
}

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

function defaultStep(): StepFormItem {
    return {
        name: '',
        type: 'action',
        next: '',
        action_type: 'send_webhook',
        config: '{}',
        expression: '',
        on_true: '',
        on_false: '',
        duration: '5m',
        poll_interval: '1m',
        timeout: '24h',
        event: 'records.create',
        collection: '',
        items: '{{trigger.records}}',
        step: '',
        branches: '[["step_a"], ["step_b"]]',
    };
}

export const DEFAULT_FORM: WorkflowFormState = {
    name: '',
    description: '',
    triggerType: 'event',
    triggerEvent: 'records.create',
    triggerCollection: '',
    triggerCondition: '',
    triggerCron: '0 9 * * *',
    steps: [],
    enabled: true,
};

// ---------------------------------------------------------------------------
// Converters
// ---------------------------------------------------------------------------

export function formToPayload(form: WorkflowFormState) {
    // Build trigger config
    let trigger: WorkflowTriggerConfig;
    switch (form.triggerType) {
        case 'event':
            trigger = {
                type: 'event',
                event: form.triggerEvent,
                ...(form.triggerCollection ? { collection: form.triggerCollection } : {}),
                ...(form.triggerCondition ? { condition: form.triggerCondition } : {}),
            };
            break;
        case 'schedule':
            trigger = { type: 'schedule', cron: form.triggerCron };
            break;
        case 'webhook':
            trigger = { type: 'webhook' };
            break;
        default:
            trigger = { type: 'manual' };
    }

    // Build steps
    const steps: WorkflowStep[] = form.steps.map((s) => {
        const base: WorkflowStep = {
            type: s.type,
            name: s.name,
            ...(s.next ? { next: s.next } : {}),
        };

        switch (s.type) {
            case 'action': {
                let config: Record<string, unknown> = {};
                try { config = JSON.parse(s.config); } catch { /* use empty */ }
                return { ...base, action_type: s.action_type, config };
            }
            case 'condition':
                return {
                    ...base,
                    expression: s.expression,
                    ...(s.on_true ? { on_true: s.on_true } : {}),
                    ...(s.on_false ? { on_false: s.on_false } : {}),
                };
            case 'wait_delay':
                return { ...base, duration: s.duration };
            case 'wait_condition':
                return {
                    ...base,
                    expression: s.expression,
                    poll_interval: s.poll_interval,
                    timeout: s.timeout,
                };
            case 'wait_event':
                return {
                    ...base,
                    event: s.event,
                    ...(s.collection ? { collection: s.collection } : {}),
                    timeout: s.timeout,
                };
            case 'loop': {
                return { ...base, items: s.items, step: s.step };
            }
            case 'parallel': {
                let branches: string[][] = [];
                try { branches = JSON.parse(s.branches); } catch { /* use empty */ }
                return { ...base, branches };
            }
            default:
                return base;
        }
    });

    return {
        name: form.name,
        description: form.description || undefined,
        trigger,
        steps,
        enabled: form.enabled,
    };
}

export function workflowToForm(wf: Workflow): WorkflowFormState {
    const tc = wf.trigger_config;
    const triggerType = wf.trigger_type as WorkflowFormState['triggerType'];

    const steps: StepFormItem[] = wf.steps.map((s) => {
        const item = defaultStep();
        item.name = String(s.name ?? '');
        item.type = String(s.type ?? 'action');
        item.next = String(s.next ?? '');

        switch (s.type) {
            case 'action':
                item.action_type = String(s.action_type ?? 'send_webhook');
                item.config = s.config ? JSON.stringify(s.config, null, 2) : '{}';
                break;
            case 'condition':
                item.expression = String(s.expression ?? '');
                item.on_true = String(s.on_true ?? '');
                item.on_false = String(s.on_false ?? '');
                break;
            case 'wait_delay':
                item.duration = String(s.duration ?? '5m');
                break;
            case 'wait_condition':
                item.expression = String(s.expression ?? '');
                item.poll_interval = String(s.poll_interval ?? '1m');
                item.timeout = String(s.timeout ?? '24h');
                break;
            case 'wait_event':
                item.event = String(s.event ?? 'records.create');
                item.collection = String(s.collection ?? '');
                item.timeout = String(s.timeout ?? '24h');
                break;
            case 'loop':
                item.items = String(s.items ?? '');
                item.step = String(s.step ?? '');
                break;
            case 'parallel':
                item.branches = s.branches ? JSON.stringify(s.branches, null, 2) : '[]';
                break;
        }
        return item;
    });

    return {
        name: wf.name,
        description: wf.description ?? '',
        triggerType,
        triggerEvent: tc.type === 'event' ? tc.event : 'records.create',
        triggerCollection: tc.type === 'event' ? (tc.collection ?? '') : '',
        triggerCondition: tc.type === 'event' ? (tc.condition ?? '') : '',
        triggerCron: tc.type === 'schedule' ? tc.cron : '0 9 * * *',
        steps,
        enabled: wf.enabled,
    };
}

// ---------------------------------------------------------------------------
// Step row component
// ---------------------------------------------------------------------------

interface StepRowProps {
    step: StepFormItem;
    index: number;
    stepNames: string[];
    onChange: (index: number, updated: StepFormItem) => void;
    onRemove: (index: number) => void;
}

function StepRow({ step, index, stepNames, onChange, onRemove }: StepRowProps) {
    const set = <K extends keyof StepFormItem>(key: K, value: StepFormItem[K]) =>
        onChange(index, { ...step, [key]: value });

    const otherStepNames = stepNames.filter((n) => n && n !== step.name);

    return (
        <div className="border rounded-md p-3 space-y-3 bg-muted/30">
            {/* Row header: step index, name, type, remove */}
            <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-muted-foreground w-5 shrink-0">
                    {index + 1}.
                </span>
                <Input
                    className="flex-1 h-8 text-xs font-mono"
                    placeholder="step_name (unique)"
                    value={step.name}
                    onChange={(e) => set('name', e.target.value)}
                />
                <Select
                    value={step.type}
                    onValueChange={(v) => onChange(index, { ...defaultStep(), name: step.name, type: v })}
                >
                    <SelectTrigger className="w-44 h-8 text-xs">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        {STEP_TYPES.map((t) => (
                            <SelectItem key={t.value} value={t.value} className="text-xs">
                                {t.label}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
                <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 shrink-0"
                    onClick={() => onRemove(index)}
                >
                    <X className="h-3.5 w-3.5" />
                </Button>
            </div>

            {/* Type-specific fields */}
            {step.type === 'action' && (
                <div className="space-y-2 pl-7">
                    <div className="flex items-center gap-2">
                        <Label className="text-xs w-20 shrink-0">Action</Label>
                        <Select
                            value={step.action_type}
                            onValueChange={(v) => set('action_type', v)}
                        >
                            <SelectTrigger className="flex-1 h-8 text-xs">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {ACTION_TYPES.map((a) => (
                                    <SelectItem key={a.value} value={a.value} className="text-xs">
                                        {a.label}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-1">
                        <Label className="text-xs">Config (JSON)</Label>
                        <Textarea
                            className="text-xs font-mono min-h-[80px]"
                            placeholder='{"url": "https://...", "method": "POST"}'
                            value={step.config}
                            onChange={(e) => set('config', e.target.value)}
                        />
                    </div>
                </div>
            )}

            {step.type === 'condition' && (
                <div className="space-y-2 pl-7">
                    <div className="space-y-1">
                        <Label className="text-xs">Expression</Label>
                        <Input
                            className="h-8 text-xs font-mono"
                            placeholder='status == "approved"'
                            value={step.expression}
                            onChange={(e) => set('expression', e.target.value)}
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                        <div className="space-y-1">
                            <Label className="text-xs">If true → step</Label>
                            <Select value={step.on_true || '__end__'} onValueChange={(v) => set('on_true', v === '__end__' ? '' : v)}>
                                <SelectTrigger className="h-8 text-xs">
                                    <SelectValue placeholder="(end)" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="__end__" className="text-xs text-muted-foreground">(end workflow)</SelectItem>
                                    {otherStepNames.map((n) => (
                                        <SelectItem key={n} value={n} className="text-xs font-mono">{n}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-1">
                            <Label className="text-xs">If false → step</Label>
                            <Select value={step.on_false || '__end__'} onValueChange={(v) => set('on_false', v === '__end__' ? '' : v)}>
                                <SelectTrigger className="h-8 text-xs">
                                    <SelectValue placeholder="(end)" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="__end__" className="text-xs text-muted-foreground">(end workflow)</SelectItem>
                                    {otherStepNames.map((n) => (
                                        <SelectItem key={n} value={n} className="text-xs font-mono">{n}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                </div>
            )}

            {step.type === 'wait_delay' && (
                <div className="pl-7 space-y-1">
                    <Label className="text-xs">Duration</Label>
                    <Input
                        className="h-8 text-xs"
                        placeholder="5m, 2h, 1d"
                        value={step.duration}
                        onChange={(e) => set('duration', e.target.value)}
                    />
                    <p className="text-xs text-muted-foreground">Supports: Ns, Nm, Nh, Nd</p>
                </div>
            )}

            {step.type === 'wait_condition' && (
                <div className="space-y-2 pl-7">
                    <div className="space-y-1">
                        <Label className="text-xs">Expression (poll until true)</Label>
                        <Input
                            className="h-8 text-xs font-mono"
                            placeholder='record.status == "approved"'
                            value={step.expression}
                            onChange={(e) => set('expression', e.target.value)}
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                        <div className="space-y-1">
                            <Label className="text-xs">Poll interval</Label>
                            <Input className="h-8 text-xs" placeholder="1m" value={step.poll_interval} onChange={(e) => set('poll_interval', e.target.value)} />
                        </div>
                        <div className="space-y-1">
                            <Label className="text-xs">Timeout</Label>
                            <Input className="h-8 text-xs" placeholder="24h" value={step.timeout} onChange={(e) => set('timeout', e.target.value)} />
                        </div>
                    </div>
                </div>
            )}

            {step.type === 'wait_event' && (
                <div className="space-y-2 pl-7">
                    <div className="flex items-center gap-2">
                        <Label className="text-xs w-20 shrink-0">Event</Label>
                        <Select value={step.event} onValueChange={(v) => set('event', v)}>
                            <SelectTrigger className="flex-1 h-8 text-xs">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {WORKFLOW_EVENTS.map((e) => (
                                    <SelectItem key={e.value} value={e.value} className="text-xs">{e.label}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                        <div className="space-y-1">
                            <Label className="text-xs">Collection (optional)</Label>
                            <Input className="h-8 text-xs" placeholder="orders" value={step.collection} onChange={(e) => set('collection', e.target.value)} />
                        </div>
                        <div className="space-y-1">
                            <Label className="text-xs">Timeout</Label>
                            <Input className="h-8 text-xs" placeholder="24h" value={step.timeout} onChange={(e) => set('timeout', e.target.value)} />
                        </div>
                    </div>
                </div>
            )}

            {step.type === 'loop' && (
                <div className="space-y-2 pl-7">
                    <div className="space-y-1">
                        <Label className="text-xs">Items expression</Label>
                        <Input
                            className="h-8 text-xs font-mono"
                            placeholder="{{trigger.records}}"
                            value={step.items}
                            onChange={(e) => set('items', e.target.value)}
                        />
                    </div>
                    <div className="space-y-1">
                        <Label className="text-xs">Step to run for each item</Label>
                        <Select value={step.step || '__none__'} onValueChange={(v) => set('step', v === '__none__' ? '' : v)}>
                            <SelectTrigger className="h-8 text-xs">
                                <SelectValue placeholder="Select step..." />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="__none__" className="text-xs text-muted-foreground">(none)</SelectItem>
                                {otherStepNames.map((n) => (
                                    <SelectItem key={n} value={n} className="text-xs font-mono">{n}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                </div>
            )}

            {step.type === 'parallel' && (
                <div className="pl-7 space-y-1">
                    <Label className="text-xs">Branches (JSON array of step name arrays)</Label>
                    <Textarea
                        className="text-xs font-mono min-h-[70px]"
                        placeholder={'[["step_a", "step_b"], ["step_c"]]'}
                        value={step.branches}
                        onChange={(e) => set('branches', e.target.value)}
                    />
                </div>
            )}

            {/* Next step (not for condition — it uses on_true/on_false) */}
            {step.type !== 'condition' && (
                <div className="flex items-center gap-2 pl-7">
                    <Label className="text-xs w-20 shrink-0">Next step</Label>
                    <Select value={step.next || '__end__'} onValueChange={(v) => set('next', v === '__end__' ? '' : v)}>
                        <SelectTrigger className="flex-1 h-8 text-xs">
                            <SelectValue placeholder="(end workflow)" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="__end__" className="text-xs text-muted-foreground">(end workflow)</SelectItem>
                            {otherStepNames.map((n) => (
                                <SelectItem key={n} value={n} className="text-xs font-mono">{n}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            )}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Main form fields component
// ---------------------------------------------------------------------------

interface WorkflowFormFieldsProps {
    form: WorkflowFormState;
    setForm: React.Dispatch<React.SetStateAction<WorkflowFormState>>;
}

export function WorkflowFormFields({ form, setForm }: WorkflowFormFieldsProps) {
    const set = <K extends keyof WorkflowFormState>(key: K, value: WorkflowFormState[K]) =>
        setForm((prev) => ({ ...prev, [key]: value }));

    const stepNames = form.steps.map((s) => s.name).filter(Boolean);

    const handleStepChange = (index: number, updated: StepFormItem) => {
        setForm((prev) => {
            const steps = [...prev.steps];
            steps[index] = updated;
            return { ...prev, steps };
        });
    };

    const handleStepRemove = (index: number) => {
        setForm((prev) => ({
            ...prev,
            steps: prev.steps.filter((_, i) => i !== index),
        }));
    };

    const addStep = () => {
        setForm((prev) => ({ ...prev, steps: [...prev.steps, defaultStep()] }));
    };

    return (
        <div className="space-y-5">
            {/* Basic info */}
            <div className="space-y-1">
                <Label htmlFor="wf-name">Name <span className="text-destructive">*</span></Label>
                <Input
                    id="wf-name"
                    placeholder="Order Approval Flow"
                    value={form.name}
                    onChange={(e) => set('name', e.target.value)}
                />
            </div>

            <div className="space-y-1">
                <Label htmlFor="wf-description">Description</Label>
                <Input
                    id="wf-description"
                    placeholder="Optional description"
                    value={form.description}
                    onChange={(e) => set('description', e.target.value)}
                />
            </div>

            {/* Trigger */}
            <div className="space-y-3">
                <div className="space-y-1">
                    <Label>Trigger</Label>
                    <Select
                        value={form.triggerType}
                        onValueChange={(v) => set('triggerType', v as WorkflowFormState['triggerType'])}
                    >
                        <SelectTrigger>
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="event">Event</SelectItem>
                            <SelectItem value="schedule">Schedule (Cron)</SelectItem>
                            <SelectItem value="manual">Manual</SelectItem>
                            <SelectItem value="webhook">Webhook</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                {form.triggerType === 'event' && (
                    <div className="space-y-2 pl-4 border-l-2 border-muted">
                        <div className="space-y-1">
                            <Label className="text-xs">Event</Label>
                            <Select value={form.triggerEvent} onValueChange={(v) => set('triggerEvent', v)}>
                                <SelectTrigger className="h-8 text-xs">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {WORKFLOW_EVENTS.map((e) => (
                                        <SelectItem key={e.value} value={e.value} className="text-xs">{e.label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        {form.triggerEvent.startsWith('records.') && (
                            <div className="space-y-1">
                                <Label className="text-xs">Collection (optional)</Label>
                                <Input
                                    className="h-8 text-xs"
                                    placeholder="orders (leave blank for all)"
                                    value={form.triggerCollection}
                                    onChange={(e) => set('triggerCollection', e.target.value)}
                                />
                            </div>
                        )}
                        <div className="space-y-1">
                            <Label className="text-xs">Condition (optional)</Label>
                            <Input
                                className="h-8 text-xs font-mono"
                                placeholder='record.status == "pending"'
                                value={form.triggerCondition}
                                onChange={(e) => set('triggerCondition', e.target.value)}
                            />
                        </div>
                    </div>
                )}

                {form.triggerType === 'schedule' && (
                    <div className="pl-4 border-l-2 border-muted space-y-1">
                        <Label className="text-xs">Cron expression</Label>
                        <Input
                            className="h-8 text-xs font-mono"
                            placeholder="0 9 * * MON"
                            value={form.triggerCron}
                            onChange={(e) => set('triggerCron', e.target.value)}
                        />
                        <p className="text-xs text-muted-foreground">
                            5-field UTC cron: minute hour day month weekday
                        </p>
                    </div>
                )}

                {form.triggerType === 'manual' && (
                    <p className="text-xs text-muted-foreground pl-4">
                        Triggered via the "Run Now" button or <code>{'POST /workflows/{id}/trigger'}</code>.
                    </p>
                )}

                {form.triggerType === 'webhook' && (
                    <p className="text-xs text-muted-foreground pl-4">
                        A unique webhook URL will be generated after saving. Anyone with the URL can trigger this workflow.
                    </p>
                )}
            </div>

            {/* Steps */}
            <div className="space-y-2">
                <div className="flex items-center justify-between">
                    <Label>Steps</Label>
                    <Button type="button" variant="outline" size="sm" className="h-7 text-xs" onClick={addStep}>
                        <Plus className="h-3.5 w-3.5 mr-1" />
                        Add Step
                    </Button>
                </div>

                {form.steps.length === 0 && (
                    <p className="text-xs text-muted-foreground text-center py-4 border rounded-md">
                        No steps yet. Click "Add Step" to build your workflow.
                    </p>
                )}

                <div className="space-y-2">
                    {form.steps.map((step, i) => (
                        <StepRow
                            key={i}
                            step={step}
                            index={i}
                            stepNames={stepNames}
                            onChange={handleStepChange}
                            onRemove={handleStepRemove}
                        />
                    ))}
                </div>

                {form.steps.length > 0 && (
                    <p className="text-xs text-muted-foreground">
                        Template vars: <code>{'{{trigger.field}}'}</code>, <code>{'{{steps.step_name.output.field}}'}</code>, <code>{'{{now}}'}</code>
                    </p>
                )}
            </div>

            {/* Enabled toggle */}
            <div className="flex items-center gap-3">
                <Switch
                    id="wf-enabled"
                    checked={form.enabled}
                    onCheckedChange={(v) => set('enabled', v)}
                />
                <Label htmlFor="wf-enabled">Enabled</Label>
            </div>
        </div>
    );
}
