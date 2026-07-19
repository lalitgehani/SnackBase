import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { HookAction } from '@/services/hooks.service';
import type { PickerOption } from './TriggerConfigCard';

interface Props {
  action: HookAction;
  onChange: (updated: HookAction) => void;
  collections: PickerOption[];
  collectionsFallback: boolean;
  emailTemplates: PickerOption[];
  emailFallback: boolean;
}

function JsonField({
  label,
  value,
  onChange,
  placeholder,
  required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
}) {
  let parseError: string | null = null;
  if (value.trim()) {
    try {
      JSON.parse(value.trim());
    } catch {
      parseError = 'Invalid JSON';
    }
  }

  return (
    <div className="space-y-1">
      <Label className="text-xs">
        {label}
        {required ? ' *' : ''}
      </Label>
      <Textarea
        className="text-xs font-mono"
        rows={3}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      {parseError && (
        <p className="text-xs text-destructive" data-testid="json-parse-error">
          {parseError}
        </p>
      )}
    </div>
  );
}

function CollectionField({
  value,
  onChange,
  collections,
  fallback,
  required,
}: {
  value: string;
  onChange: (v: string) => void;
  collections: PickerOption[];
  fallback: boolean;
  required?: boolean;
}) {
  if (fallback || collections.length === 0) {
    return (
      <div className="space-y-1">
        <Label className="text-xs">Collection{required ? ' *' : ''}</Label>
        <Input
          className="h-8 text-xs"
          placeholder="collection name"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          data-testid="action-collection-input"
        />
        <p className="text-xs text-muted-foreground">Enter id / name manually</p>
      </div>
    );
  }
  return (
    <div className="space-y-1">
      <Label className="text-xs">Collection{required ? ' *' : ''}</Label>
      <Select value={value || undefined} onValueChange={onChange}>
        <SelectTrigger className="h-8 text-xs" data-testid="action-collection-select">
          <SelectValue placeholder="Select collection" />
        </SelectTrigger>
        <SelectContent>
          {collections.map((c) => (
            <SelectItem key={c.value} value={c.value} className="text-xs">
              {c.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

export function ActionTypeFields({
  action,
  onChange,
  collections,
  collectionsFallback,
  emailTemplates,
  emailFallback,
}: Props) {
  const set = (key: string, value: string) => onChange({ ...action, [key]: value });

  if (action.type === 'send_webhook') {
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-3 gap-2">
          <div className="col-span-2 space-y-1">
            <Label className="text-xs">URL *</Label>
            <Input
              className="h-8 text-xs"
              placeholder="https://example.com/webhook"
              value={String(action.url ?? '')}
              onChange={(e) => set('url', e.target.value)}
              data-testid="action-webhook-url"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Method</Label>
            <Select
              value={String(action.method ?? 'POST')}
              onValueChange={(v) => set('method', v)}
            >
              <SelectTrigger className="h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {['POST', 'PUT', 'PATCH', 'GET'].map((m) => (
                  <SelectItem key={m} value={m} className="text-xs">
                    {m}
                  </SelectItem>
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
            placeholder='{"user": "{{auth.user_id}}"}'
            value={String(action.body_template ?? '')}
            onChange={(e) => set('body_template', e.target.value)}
          />
        </div>
        <JsonField
          label="Headers JSON (optional)"
          value={String(action.headers ?? '')}
          onChange={(v) => set('headers', v)}
          placeholder='{"Authorization": "Bearer token"}'
        />
      </div>
    );
  }

  if (action.type === 'send_email') {
    return (
      <div className="space-y-3">
        <div className="space-y-1">
          <Label className="text-xs">To *</Label>
          <Input
            className="h-8 text-xs"
            placeholder="user@example.com or {{record.email}}"
            value={String(action.to ?? '')}
            onChange={(e) => set('to', e.target.value)}
            data-testid="action-email-to"
          />
        </div>
        <div className="space-y-1">
          <Label className="text-xs">Subject *</Label>
          <Input
            className="h-8 text-xs"
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
            value={String(action.body ?? '')}
            onChange={(e) => set('body', e.target.value)}
          />
        </div>
        <div className="space-y-1">
          <Label className="text-xs">Template ID (optional, overrides body)</Label>
          {emailFallback || emailTemplates.length === 0 ? (
            <>
              <Input
                className="h-8 text-xs"
                placeholder="welcome or template uuid"
                value={String(action.template_id ?? '')}
                onChange={(e) => set('template_id', e.target.value)}
                data-testid="action-template-input"
              />
              <p className="text-xs text-muted-foreground">Enter id / name manually</p>
            </>
          ) : (
            <Select
              value={String(action.template_id || '__none__')}
              onValueChange={(v) => set('template_id', v === '__none__' ? '' : v)}
            >
              <SelectTrigger className="h-8 text-xs" data-testid="action-template-select">
                <SelectValue placeholder="None" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__" className="text-xs">
                  None
                </SelectItem>
                {emailTemplates.map((t) => (
                  <SelectItem key={t.value} value={t.value} className="text-xs">
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
      </div>
    );
  }

  if (action.type === 'create_record') {
    return (
      <div className="space-y-3">
        <CollectionField
          value={String(action.collection ?? '')}
          onChange={(v) => set('collection', v)}
          collections={collections}
          fallback={collectionsFallback}
          required
        />
        <JsonField
          label="Data (JSON)"
          value={String(action.data ?? '{}')}
          onChange={(v) => set('data', v)}
          required
        />
      </div>
    );
  }

  if (action.type === 'update_record') {
    return (
      <div className="space-y-3">
        <CollectionField
          value={String(action.collection ?? '')}
          onChange={(v) => set('collection', v)}
          collections={collections}
          fallback={collectionsFallback}
          required
        />
        <div className="space-y-1">
          <Label className="text-xs">Record ID *</Label>
          <Input
            className="h-8 text-xs"
            placeholder="{{record.id}}"
            value={String(action.record_id ?? '')}
            onChange={(e) => set('record_id', e.target.value)}
          />
        </div>
        <JsonField
          label="Data (JSON)"
          value={String(action.data ?? '{}')}
          onChange={(v) => set('data', v)}
          required
        />
      </div>
    );
  }

  if (action.type === 'delete_record') {
    return (
      <div className="space-y-3">
        <CollectionField
          value={String(action.collection ?? '')}
          onChange={(v) => set('collection', v)}
          collections={collections}
          fallback={collectionsFallback}
          required
        />
        <div className="space-y-1">
          <Label className="text-xs">Record ID *</Label>
          <Input
            className="h-8 text-xs"
            placeholder="{{record.id}}"
            value={String(action.record_id ?? '')}
            onChange={(e) => set('record_id', e.target.value)}
          />
        </div>
      </div>
    );
  }

  if (action.type === 'enqueue_job') {
    return (
      <div className="space-y-3">
        <div className="space-y-1">
          <Label className="text-xs">Handler *</Label>
          <Input
            className="h-8 text-xs"
            placeholder="send_notification"
            value={String(action.handler ?? '')}
            onChange={(e) => set('handler', e.target.value)}
            data-testid="action-job-handler"
          />
        </div>
        <JsonField
          label="Payload (JSON, optional)"
          value={String(action.payload ?? '{}')}
          onChange={(v) => set('payload', v)}
        />
      </div>
    );
  }

  return <p className="text-xs text-muted-foreground">Unknown action type.</p>;
}
