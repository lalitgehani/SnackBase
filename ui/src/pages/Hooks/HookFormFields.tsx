/**
 * Shared form fields for CreateHookDialog and EditHookDialog.
 * Extracted to avoid duplication.
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
import type { HookAction } from '@/services/hooks.service';

export const HOOK_EVENTS = [
    { value: 'records.create', label: 'records.create — Record created' },
    { value: 'records.update', label: 'records.update — Record updated' },
    { value: 'records.delete', label: 'records.delete — Record deleted' },
    { value: 'auth.login', label: 'auth.login — User logged in' },
    { value: 'auth.register', label: 'auth.register — User registered' },
] as const;

export const ACTION_TYPES = [
    { value: 'send_webhook', label: 'Send Webhook' },
    { value: 'send_email', label: 'Send Email' },
    { value: 'create_record', label: 'Create Record' },
    { value: 'update_record', label: 'Update Record' },
    { value: 'delete_record', label: 'Delete Record' },
    { value: 'enqueue_job', label: 'Enqueue Job' },
] as const;

export interface HookFormState {
    name: string;
    description: string;
    triggerType: 'event' | 'manual';
    event: string;
    collection: string;
    condition: string;
    actions: HookAction[];
    enabled: boolean;
}

export const DEFAULT_FORM: HookFormState = {
    name: '',
    description: '',
    triggerType: 'event',
    event: 'records.create',
    collection: '',
    condition: '',
    actions: [],
    enabled: true,
};

function isRecordEvent(event: string) {
    return event.startsWith('records.');
}

function newAction(type: string): HookAction {
    switch (type) {
        case 'send_webhook':
            return { type, url: '', method: 'POST', headers: '', body_template: '' };
        case 'send_email':
            return { type, to: '', subject: '', body: '', template_id: '' };
        case 'create_record':
            return { type, collection: '', data: '{}' };
        case 'update_record':
            return { type, collection: '', record_id: '', data: '{}' };
        case 'delete_record':
            return { type, collection: '', record_id: '' };
        case 'enqueue_job':
            return { type, handler: '', payload: '{}' };
        default:
            return { type };
    }
}

interface ActionRowProps {
    action: HookAction;
    index: number;
    onChange: (index: number, updated: HookAction) => void;
    onRemove: (index: number) => void;
}

function ActionRow({ action, index, onChange, onRemove }: ActionRowProps) {
    const set = (key: string, value: string) => onChange(index, { ...action, [key]: value });

    return (
        <div className="border rounded-md p-3 space-y-3 bg-muted/30">
            <div className="flex items-center gap-2">
                <Select
                    value={action.type}
                    onValueChange={(v) => onChange(index, newAction(v))}
                >
                    <SelectTrigger className="flex-1 h-8 text-xs">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        {ACTION_TYPES.map((at) => (
                            <SelectItem key={at.value} value={at.value} className="text-xs">
                                {at.label}
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

            {action.type === 'send_webhook' && (
                <div className="space-y-2">
                    <div className="grid grid-cols-3 gap-2">
                        <div className="col-span-2 space-y-1">
                            <Label className="text-xs">URL *</Label>
                            <Input
                                className="h-7 text-xs"
                                placeholder="https://example.com/webhook"
                                value={String(action.url ?? '')}
                                onChange={(e) => set('url', e.target.value)}
                            />
                        </div>
                        <div className="space-y-1">
                            <Label className="text-xs">Method</Label>
                            <Select value={String(action.method ?? 'POST')} onValueChange={(v) => set('method', v)}>
                                <SelectTrigger className="h-7 text-xs">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {['POST', 'PUT', 'PATCH', 'GET'].map((m) => (
                                        <SelectItem key={m} value={m} className="text-xs">{m}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    <div className="space-y-1">
                        <Label className="text-xs">Body template (optional)</Label>
                        <Textarea
                            className="text-xs font-mono"
                            rows={2}
                            placeholder='{"user": "{{auth.user_id}}", "record": "{{record.id}}"}'
                            value={String(action.body_template ?? '')}
                            onChange={(e) => set('body_template', e.target.value)}
                        />
                    </div>
                    <div className="space-y-1">
                        <Label className="text-xs">Headers JSON (optional)</Label>
                        <Textarea
                            className="text-xs font-mono"
                            rows={2}
                            placeholder='{"Authorization": "Bearer token"}'
                            value={String(action.headers ?? '')}
                            onChange={(e) => set('headers', e.target.value)}
                        />
                    </div>
                </div>
            )}

            {action.type === 'send_email' && (
                <div className="space-y-2">
                    <div className="space-y-1">
                        <Label className="text-xs">To *</Label>
                        <Input
                            className="h-7 text-xs"
                            placeholder="user@example.com or {{record.email}}"
                            value={String(action.to ?? '')}
                            onChange={(e) => set('to', e.target.value)}
                        />
                    </div>
                    <div className="space-y-1">
                        <Label className="text-xs">Subject *</Label>
                        <Input
                            className="h-7 text-xs"
                            placeholder="Notification: {{record.id}}"
                            value={String(action.subject ?? '')}
                            onChange={(e) => set('subject', e.target.value)}
                        />
                    </div>
                    <div className="space-y-1">
                        <Label className="text-xs">Body</Label>
                        <Textarea
                            className="text-xs"
                            rows={2}
                            placeholder="Hello {{auth.email}}, a new record was created."
                            value={String(action.body ?? '')}
                            onChange={(e) => set('body', e.target.value)}
                        />
                    </div>
                    <div className="space-y-1">
                        <Label className="text-xs">Template ID (optional, overrides body)</Label>
                        <Input
                            className="h-7 text-xs"
                            placeholder="welcome"
                            value={String(action.template_id ?? '')}
                            onChange={(e) => set('template_id', e.target.value)}
                        />
                    </div>
                </div>
            )}

            {action.type === 'create_record' && (
                <div className="space-y-2">
                    <div className="space-y-1">
                        <Label className="text-xs">Collection *</Label>
                        <Input
                            className="h-7 text-xs"
                            placeholder="logs"
                            value={String(action.collection ?? '')}
                            onChange={(e) => set('collection', e.target.value)}
                        />
                    </div>
                    <div className="space-y-1">
                        <Label className="text-xs">Data (JSON) *</Label>
                        <Textarea
                            className="text-xs font-mono"
                            rows={3}
                            placeholder='{"message": "Record {{record.id}} created by {{auth.email}}"}'
                            value={String(action.data ?? '{}')}
                            onChange={(e) => set('data', e.target.value)}
                        />
                    </div>
                </div>
            )}

            {action.type === 'update_record' && (
                <div className="space-y-2">
                    <div className="space-y-1">
                        <Label className="text-xs">Collection *</Label>
                        <Input
                            className="h-7 text-xs"
                            placeholder="posts"
                            value={String(action.collection ?? '')}
                            onChange={(e) => set('collection', e.target.value)}
                        />
                    </div>
                    <div className="space-y-1">
                        <Label className="text-xs">Record ID *</Label>
                        <Input
                            className="h-7 text-xs"
                            placeholder="{{record.id}}"
                            value={String(action.record_id ?? '')}
                            onChange={(e) => set('record_id', e.target.value)}
                        />
                    </div>
                    <div className="space-y-1">
                        <Label className="text-xs">Data (JSON) *</Label>
                        <Textarea
                            className="text-xs font-mono"
                            rows={3}
                            placeholder='{"status": "published"}'
                            value={String(action.data ?? '{}')}
                            onChange={(e) => set('data', e.target.value)}
                        />
                    </div>
                </div>
            )}

            {action.type === 'delete_record' && (
                <div className="space-y-2">
                    <div className="space-y-1">
                        <Label className="text-xs">Collection *</Label>
                        <Input
                            className="h-7 text-xs"
                            placeholder="drafts"
                            value={String(action.collection ?? '')}
                            onChange={(e) => set('collection', e.target.value)}
                        />
                    </div>
                    <div className="space-y-1">
                        <Label className="text-xs">Record ID *</Label>
                        <Input
                            className="h-7 text-xs"
                            placeholder="{{record.id}}"
                            value={String(action.record_id ?? '')}
                            onChange={(e) => set('record_id', e.target.value)}
                        />
                    </div>
                </div>
            )}

            {action.type === 'enqueue_job' && (
                <div className="space-y-2">
                    <div className="space-y-1">
                        <Label className="text-xs">Handler *</Label>
                        <Input
                            className="h-7 text-xs"
                            placeholder="send_notification"
                            value={String(action.handler ?? '')}
                            onChange={(e) => set('handler', e.target.value)}
                        />
                    </div>
                    <div className="space-y-1">
                        <Label className="text-xs">Payload (JSON, optional)</Label>
                        <Textarea
                            className="text-xs font-mono"
                            rows={2}
                            placeholder='{"user_id": "{{auth.user_id}}"}'
                            value={String(action.payload ?? '{}')}
                            onChange={(e) => set('payload', e.target.value)}
                        />
                    </div>
                </div>
            )}
        </div>
    );
}

interface HookFormFieldsProps {
    form: HookFormState;
    setForm: (form: HookFormState) => void;
    idPrefix?: string;
}

export function HookFormFields({ form, setForm, idPrefix = '' }: HookFormFieldsProps) {
    const id = (s: string) => `${idPrefix}${s}`;

    const updateAction = (index: number, updated: HookAction) => {
        const actions = [...form.actions];
        actions[index] = updated;
        setForm({ ...form, actions });
    };

    const removeAction = (index: number) => {
        setForm({ ...form, actions: form.actions.filter((_, i) => i !== index) });
    };

    const addAction = () => {
        setForm({ ...form, actions: [...form.actions, newAction('send_webhook')] });
    };

    return (
        <div className="space-y-4 py-4">
            {/* Basic info */}
            <div className="space-y-1.5">
                <Label htmlFor={id('name')}>Name *</Label>
                <Input
                    id={id('name')}
                    placeholder="e.g. Notify on new post"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    required
                />
            </div>

            <div className="space-y-1.5">
                <Label htmlFor={id('description')}>Description (optional)</Label>
                <Textarea
                    id={id('description')}
                    placeholder="What does this hook do?"
                    rows={2}
                    value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
            </div>

            {/* Trigger configuration */}
            <div className="space-y-3 border rounded-md p-3">
                <p className="text-sm font-medium">Trigger</p>
                <div className="space-y-1.5">
                    <Label htmlFor={id('trigger-type')}>Trigger type</Label>
                    <Select
                        value={form.triggerType}
                        onValueChange={(v: 'event' | 'manual') => setForm({ ...form, triggerType: v })}
                    >
                        <SelectTrigger id={id('trigger-type')}>
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="event">Event-triggered</SelectItem>
                            <SelectItem value="manual">Manual only</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                {form.triggerType === 'event' && (
                    <>
                        <div className="space-y-1.5">
                            <Label htmlFor={id('event')}>Event</Label>
                            <Select
                                value={form.event}
                                onValueChange={(v) => setForm({ ...form, event: v, collection: isRecordEvent(v) ? form.collection : '' })}
                            >
                                <SelectTrigger id={id('event')}>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {HOOK_EVENTS.map((e) => (
                                        <SelectItem key={e.value} value={e.value}>
                                            {e.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        {isRecordEvent(form.event) && (
                            <div className="space-y-1.5">
                                <Label htmlFor={id('collection')}>Collection filter (optional)</Label>
                                <Input
                                    id={id('collection')}
                                    placeholder="e.g. posts (leave blank for all collections)"
                                    value={form.collection}
                                    onChange={(e) => setForm({ ...form, collection: e.target.value })}
                                />
                            </div>
                        )}
                    </>
                )}
            </div>

            {/* Condition */}
            <div className="space-y-1.5">
                <Label htmlFor={id('condition')}>
                    Condition{' '}
                    <span className="font-normal text-muted-foreground">(optional)</span>
                </Label>
                <Input
                    id={id('condition')}
                    placeholder='status = "active" AND role != "admin"'
                    value={form.condition}
                    onChange={(e) => setForm({ ...form, condition: e.target.value })}
                />
                <p className="text-xs text-muted-foreground">
                    Rule expression that must be true for actions to execute.
                </p>
            </div>

            {/* Actions builder */}
            <div className="space-y-2">
                <div className="flex items-center justify-between">
                    <Label>Actions</Label>
                    <Button type="button" variant="outline" size="sm" className="h-7 text-xs" onClick={addAction}>
                        <Plus className="h-3.5 w-3.5 mr-1" />
                        Add Action
                    </Button>
                </div>

                {form.actions.length === 0 ? (
                    <p className="text-xs text-muted-foreground py-2">
                        No actions yet. Add at least one action to execute when the hook fires.
                    </p>
                ) : (
                    <div className="space-y-2">
                        {form.actions.map((action, i) => (
                            <ActionRow
                                key={i}
                                action={action}
                                index={i}
                                onChange={updateAction}
                                onRemove={removeAction}
                            />
                        ))}
                    </div>
                )}

                <p className="text-xs text-muted-foreground">
                    Available variables: <code className="bg-muted px-1 rounded">{'{{record.field}}'}</code>{' '}
                    <code className="bg-muted px-1 rounded">{'{{auth.user_id}}'}</code>{' '}
                    <code className="bg-muted px-1 rounded">{'{{auth.email}}'}</code>{' '}
                    <code className="bg-muted px-1 rounded">{'{{now}}'}</code>
                </p>
            </div>

            {/* Enabled */}
            <div className="flex items-center gap-3">
                <Switch
                    id={id('enabled')}
                    checked={form.enabled}
                    onCheckedChange={(v) => setForm({ ...form, enabled: v })}
                />
                <Label htmlFor={id('enabled')}>Enable immediately</Label>
            </div>
        </div>
    );
}

/** Convert form state → API request payload */
export function formToPayload(form: HookFormState) {
    const trigger =
        form.triggerType === 'event'
            ? {
                  type: 'event' as const,
                  event: form.event,
                  ...(isRecordEvent(form.event) && form.collection.trim()
                      ? { collection: form.collection.trim() }
                      : {}),
              }
            : { type: 'manual' as const };

    // Parse JSON fields in actions back to objects
    const actions = form.actions.map((a) => {
        const parsed: HookAction = { ...a };
        for (const key of ['headers', 'data', 'payload'] as const) {
            const raw = parsed[key];
            if (typeof raw === 'string' && raw.trim()) {
                try {
                    parsed[key] = JSON.parse(raw.trim());
                } catch {
                    // leave as string; backend will validate
                }
            } else if (typeof raw === 'string' && !raw.trim()) {
                delete parsed[key];
            }
        }
        // Clean empty optional strings
        for (const key of ['body_template', 'template_id', 'body'] as const) {
            if (typeof parsed[key] === 'string' && !(parsed[key] as string).trim()) {
                delete parsed[key];
            }
        }
        return parsed;
    });

    return {
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        trigger,
        condition: form.condition.trim() || undefined,
        actions,
        enabled: form.enabled,
    };
}

/** Convert an existing Hook → form state */
export function hookToForm(hook: { name: string; description: string | null; trigger: { type: string; event?: string; collection?: string }; condition: string | null; actions: HookAction[]; enabled: boolean }): HookFormState {
    const triggerType = hook.trigger.type === 'manual' ? 'manual' : 'event';

    // Serialize object fields back to JSON strings for editing
    const actions = hook.actions.map((a) => {
        const copy: HookAction = { ...a };
        for (const key of ['headers', 'data', 'payload'] as const) {
            const v = copy[key];
            if (v !== null && v !== undefined && typeof v === 'object') {
                copy[key] = JSON.stringify(v, null, 2);
            }
        }
        return copy;
    });

    return {
        name: hook.name,
        description: hook.description ?? '',
        triggerType,
        event: (hook.trigger as { event?: string }).event ?? 'records.create',
        collection: (hook.trigger as { collection?: string }).collection ?? '',
        condition: hook.condition ?? '',
        actions,
        enabled: hook.enabled,
    };
}
