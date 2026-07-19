import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { HookAction } from '@/services/hooks.service';
import { ACTION_TYPES } from '../hookConstants';
import { newAction } from './hookFormState';
import { ActionTypeFields } from './ActionTypeFields';
import type { PickerOption } from './TriggerConfigCard';

interface Props {
  action: HookAction | null;
  selectedIndex: number | null;
  onChange: (updated: HookAction) => void;
  collections: PickerOption[];
  collectionsFallback: boolean;
  emailTemplates: PickerOption[];
  emailFallback: boolean;
}

export function ActionPropertiesPanel({
  action,
  selectedIndex,
  onChange,
  collections,
  collectionsFallback,
  emailTemplates,
  emailFallback,
}: Props) {
  if (action === null || selectedIndex === null) {
    return (
      <div
        className="flex flex-col h-full items-center justify-center p-6 text-center"
        data-testid="action-properties-empty"
      >
        <p className="text-sm text-muted-foreground">
          Select an action in the pipeline to edit its properties.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-h-0" data-testid="action-properties-panel">
      <div className="shrink-0 border-b px-3 py-2">
        <p className="text-sm font-medium">
          Action {selectedIndex + 1} properties
        </p>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        <div className="space-y-1">
          <Label className="text-xs">Type</Label>
          <Select
            value={action.type}
            onValueChange={(v) => onChange(newAction(v))}
          >
            <SelectTrigger className="h-8 text-xs" data-testid="action-type-select">
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
        </div>
        <ActionTypeFields
          action={action}
          onChange={onChange}
          collections={collections}
          collectionsFallback={collectionsFallback}
          emailTemplates={emailTemplates}
          emailFallback={emailFallback}
        />
      </div>
    </div>
  );
}
