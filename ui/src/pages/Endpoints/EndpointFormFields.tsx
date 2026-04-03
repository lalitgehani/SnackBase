/**
 * Shared form fields for CreateEndpointDialog and EditEndpointDialog.
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
import type { EndpointAction } from '@/services/endpoints.service';

export const HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'] as const;

export const ACTION_TYPES = [
    { value: 'send_webhook', label: 'Send Webhook' },
    { value: 'send_email', label: 'Send Email' },
    { value: 'create_record', label: 'Create Record' },
    { value: 'update_record', label: 'Update Record' },
    { value: 'delete_record', label: 'Delete Record' },
    { value: 'enqueue_job', label: 'Enqueue Job' },
] as const;

export interface EndpointFormState {
    name: string;
    description: string;
    method: string;
    path: string;
    auth_required: boolean;
    condition: string;
    actions: EndpointAction[];
    response_template: string;
    enabled: boolean;
}

export const DEFAULT_FORM: EndpointFormState = {
    name: '',
    description: '',
    method: 'POST',
    path: '/',
    auth_required: true,
    condition: '',
    actions: [],
    response_template: '',
    enabled: true,
};

function newAction(type: string): EndpointAction {
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
    action: EndpointAction;
    index: number;
    onChange: (index: number, updated: EndpointAction) => void;
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
                            placeholder='{"user": "{{auth.user_id}}", "data": "{{request.body.field}}"}'
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
                            placeholder="user@example.com or {{request.body.email}}"
                            value={String(action.to ?? '')}
                            onChange={(e) => set('to', e.target.value)}
                        />
                    </div>
                    <div className="space-y-1">
                        <Label className="text-xs">Subject *</Label>
                        <Input
                            className="h-7 text-xs"
                            placeholder="Hello from {{auth.email}}"
                            value={String(action.subject ?? '')}
                            onChange={(e) => set('subject', e.target.value)}
                        />
                    </div>
                    <div className="space-y-1">
                        <Label className="text-xs">Body</Label>
                        <Textarea
                            className="text-xs"
                            rows={2}
                            placeholder="Request from {{auth.email}}"
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
                            placeholder='{"message": "{{request.body.message}}", "user": "{{auth.user_id}}"}'
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
                            placeholder="{{request.params.id}}"
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
                            placeholder="{{request.params.id}}"
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

interface EndpointFormFieldsProps {
    form: EndpointFormState;
    setForm: (form: EndpointFormState) => void;
    accountSlug?: string;
    idPrefix?: string;
}

export function EndpointFormFields({ form, setForm, accountSlug, idPrefix = '' }: EndpointFormFieldsProps) {
    const id = (s: string) => `${idPrefix}${s}`;

    const updateAction = (index: number, updated: EndpointAction) => {
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

    const previewUrl = accountSlug
        ? `/api/v1/x/${accountSlug}${form.path || '/'}`
        : `/api/v1/x/{account_slug}${form.path || '/'}`;

    return (
        <div className="space-y-4 py-4">
            {/* Basic info */}
            <div className="space-y-1.5">
                <Label htmlFor={id('name')}>Name *</Label>
                <Input
                    id={id('name')}
                    placeholder="e.g. Create user profile"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    required
                />
            </div>

            <div className="space-y-1.5">
                <Label htmlFor={id('description')}>Description (optional)</Label>
                <Textarea
                    id={id('description')}
                    placeholder="What does this endpoint do?"
                    rows={2}
                    value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
            </div>

            {/* Endpoint configuration */}
            <div className="space-y-3 border rounded-md p-3">
                <p className="text-sm font-medium">Configuration</p>

                <div className="grid grid-cols-3 gap-3">
                    <div className="space-y-1.5">
                        <Label htmlFor={id('method')}>Method</Label>
                        <Select
                            value={form.method}
                            onValueChange={(v) => setForm({ ...form, method: v })}
                        >
                            <SelectTrigger id={id('method')}>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {HTTP_METHODS.map((m) => (
                                    <SelectItem key={m} value={m}>{m}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="col-span-2 space-y-1.5">
                        <Label htmlFor={id('path')}>Path *</Label>
                        <Input
                            id={id('path')}
                            placeholder="/hello or /users/:id/profile"
                            value={form.path}
                            onChange={(e) => setForm({ ...form, path: e.target.value })}
                            className="font-mono text-sm"
                        />
                    </div>
                </div>

                <div className="rounded bg-muted px-3 py-1.5">
                    <p className="text-xs text-muted-foreground">
                        URL:{' '}
                        <code className="font-mono text-xs text-foreground">{previewUrl}</code>
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    <Switch
                        id={id('auth_required')}
                        checked={form.auth_required}
                        onCheckedChange={(v) => setForm({ ...form, auth_required: v })}
                    />
                    <Label htmlFor={id('auth_required')}>Require authentication</Label>
                </div>

                <div className="space-y-1.5">
                    <Label htmlFor={id('condition')}>
                        Condition{' '}
                        <span className="font-normal text-muted-foreground">(optional)</span>
                    </Label>
                    <Input
                        id={id('condition')}
                        placeholder='role = "admin" or user.id == request.params.id'
                        value={form.condition}
                        onChange={(e) => setForm({ ...form, condition: e.target.value })}
                    />
                    <p className="text-xs text-muted-foreground">
                        Rule expression evaluated before executing actions. Returns 403 if false.
                    </p>
                </div>
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
                        No actions yet. Add actions to run when this endpoint is called.
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
                    Variables:{' '}
                    <code className="bg-muted px-1 rounded">{'{{request.body.field}}'}</code>{' '}
                    <code className="bg-muted px-1 rounded">{'{{request.query.field}}'}</code>{' '}
                    <code className="bg-muted px-1 rounded">{'{{request.params.field}}'}</code>{' '}
                    <code className="bg-muted px-1 rounded">{'{{auth.user_id}}'}</code>{' '}
                    <code className="bg-muted px-1 rounded">{'{{actions[0].result}}'}</code>
                </p>
            </div>

            {/* Response template */}
            <div className="space-y-1.5">
                <Label htmlFor={id('response_template')}>
                    Response template{' '}
                    <span className="font-normal text-muted-foreground">(optional)</span>
                </Label>
                <Textarea
                    id={id('response_template')}
                    className="text-xs font-mono"
                    rows={4}
                    placeholder={`{\n  "status": 200,\n  "body": {"message": "ok", "result": "{{actions[0].result}}"},\n  "headers": {"X-Custom": "value"}\n}`}
                    value={form.response_template}
                    onChange={(e) => setForm({ ...form, response_template: e.target.value })}
                />
                <p className="text-xs text-muted-foreground">
                    JSON with <code className="bg-muted px-1 rounded">status</code>,{' '}
                    <code className="bg-muted px-1 rounded">body</code>, and optional{' '}
                    <code className="bg-muted px-1 rounded">headers</code>. Leave blank to return the last action result.
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

/** Convert form state → API payload */
export function formToPayload(form: EndpointFormState) {
    // Parse response_template JSON
    let response_template: Record<string, unknown> | undefined;
    if (form.response_template.trim()) {
        try {
            response_template = JSON.parse(form.response_template.trim());
        } catch {
            // leave undefined; backend will reject if malformed
        }
    }

    // Parse JSON fields in actions
    const actions = form.actions.map((a) => {
        const parsed: EndpointAction = { ...a };
        for (const key of ['headers', 'data', 'payload'] as const) {
            const raw = parsed[key];
            if (typeof raw === 'string' && raw.trim()) {
                try {
                    parsed[key] = JSON.parse(raw.trim());
                } catch {
                    // leave as string
                }
            } else if (typeof raw === 'string' && !raw.trim()) {
                delete parsed[key];
            }
        }
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
        path: form.path.trim(),
        method: form.method,
        auth_required: form.auth_required,
        condition: form.condition.trim() || undefined,
        actions,
        response_template,
        enabled: form.enabled,
    };
}

/** Convert an existing Endpoint → form state */
export function endpointToForm(endpoint: {
    name: string;
    description: string | null;
    path: string;
    method: string;
    auth_required: boolean;
    condition: string | null;
    actions: EndpointAction[];
    response_template: Record<string, unknown> | null;
    enabled: boolean;
}): EndpointFormState {
    const actions = endpoint.actions.map((a) => {
        const copy: EndpointAction = { ...a };
        for (const key of ['headers', 'data', 'payload'] as const) {
            const v = copy[key];
            if (v !== null && v !== undefined && typeof v === 'object') {
                copy[key] = JSON.stringify(v, null, 2);
            }
        }
        return copy;
    });

    return {
        name: endpoint.name,
        description: endpoint.description ?? '',
        method: endpoint.method,
        path: endpoint.path,
        auth_required: endpoint.auth_required,
        condition: endpoint.condition ?? '',
        actions,
        response_template: endpoint.response_template
            ? JSON.stringify(endpoint.response_template, null, 2)
            : '',
        enabled: endpoint.enabled,
    };
}
