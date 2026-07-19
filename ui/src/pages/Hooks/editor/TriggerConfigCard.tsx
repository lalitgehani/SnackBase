import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { HOOK_EVENTS } from '../hookConstants';
import { isRecordEvent, type HookFormState } from './hookFormState';

export interface PickerOption {
  value: string;
  label: string;
}

interface Props {
  form: HookFormState;
  onChange: (patch: Partial<HookFormState>) => void;
  collections: PickerOption[];
  collectionsLoading: boolean;
  collectionsFallback: boolean;
}

export function TriggerConfigCard({
  form,
  onChange,
  collections,
  collectionsLoading,
  collectionsFallback,
}: Props) {
  return (
    <div className="rounded-lg border bg-card p-3 space-y-3" data-testid="trigger-config-card">
      <p className="text-sm font-medium">Trigger</p>
      <div className="space-y-1.5">
        <Label htmlFor="hook-trigger-type">Trigger type</Label>
        <Select
          value={form.triggerType}
          onValueChange={(v: 'event' | 'manual') => onChange({ triggerType: v })}
        >
          <SelectTrigger id="hook-trigger-type" data-testid="trigger-type-select">
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
            <Label htmlFor="hook-event">Event</Label>
            <Select
              value={form.event}
              onValueChange={(v) =>
                onChange({
                  event: v,
                  collection: isRecordEvent(v) ? form.collection : '',
                })
              }
            >
              <SelectTrigger id="hook-event" data-testid="trigger-event-select">
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
              <Label htmlFor="hook-collection-filter">Collection filter (optional)</Label>
              {collectionsFallback || collections.length === 0 ? (
                <>
                  <Input
                    id="hook-collection-filter"
                    placeholder="e.g. posts (blank = all)"
                    value={form.collection}
                    onChange={(e) => onChange({ collection: e.target.value })}
                    data-testid="trigger-collection-input"
                  />
                  <p className="text-xs text-muted-foreground">
                    Enter collection name manually
                    {collectionsLoading ? ' (loading list…)' : ''}
                  </p>
                </>
              ) : (
                <Select
                  value={form.collection || '__all__'}
                  onValueChange={(v) =>
                    onChange({ collection: v === '__all__' ? '' : v })
                  }
                >
                  <SelectTrigger id="hook-collection-filter" data-testid="trigger-collection-select">
                    <SelectValue placeholder="All collections" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__">All collections</SelectItem>
                    {collections.map((c) => (
                      <SelectItem key={c.value} value={c.value}>
                        {c.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
