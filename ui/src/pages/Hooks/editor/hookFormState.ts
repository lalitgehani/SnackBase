/**
 * Pure form state, payload mapping, and validation for the hook editor.
 */

import type {
  CreateHookRequest,
  Hook,
  HookAction,
  HookTrigger,
} from '@/services/hooks.service';

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

export function isRecordEvent(event: string): boolean {
  return event.startsWith('records.');
}

export function newAction(type: string): HookAction {
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

export type ValidateResult =
  | { ok: true }
  | { ok: false; errors: string[] };

function tryParseJsonField(
  raw: unknown,
  fieldLabel: string,
  errors: string[],
): unknown {
  if (typeof raw !== 'string') return raw;
  if (!raw.trim()) return undefined;
  try {
    return JSON.parse(raw.trim());
  } catch {
    errors.push(`${fieldLabel} must be valid JSON`);
    return raw;
  }
}

export function validateHookForm(form: HookFormState): ValidateResult {
  const errors: string[] = [];

  if (!form.name.trim()) {
    errors.push('Name is required');
  }

  if (form.actions.length === 0) {
    errors.push('Add at least one action');
  }

  form.actions.forEach((action, index) => {
    const label = `Action ${index + 1}`;
    switch (action.type) {
      case 'send_webhook': {
        if (!String(action.url ?? '').trim()) {
          errors.push(`${label}: Webhook URL is required`);
        }
        if (typeof action.headers === 'string' && action.headers.trim()) {
          tryParseJsonField(action.headers, `${label}: Headers`, errors);
        }
        break;
      }
      case 'send_email': {
        if (!String(action.to ?? '').trim()) {
          errors.push(`${label}: Email "to" is required`);
        }
        if (!String(action.subject ?? '').trim() && !String(action.template_id ?? '').trim()) {
          errors.push(`${label}: Subject is required (or set a template id)`);
        }
        break;
      }
      case 'create_record': {
        if (!String(action.collection ?? '').trim()) {
          errors.push(`${label}: Collection is required`);
        }
        tryParseJsonField(action.data, `${label}: Data`, errors);
        break;
      }
      case 'update_record': {
        if (!String(action.collection ?? '').trim()) {
          errors.push(`${label}: Collection is required`);
        }
        if (!String(action.record_id ?? '').trim()) {
          errors.push(`${label}: Record ID is required`);
        }
        tryParseJsonField(action.data, `${label}: Data`, errors);
        break;
      }
      case 'delete_record': {
        if (!String(action.collection ?? '').trim()) {
          errors.push(`${label}: Collection is required`);
        }
        if (!String(action.record_id ?? '').trim()) {
          errors.push(`${label}: Record ID is required`);
        }
        break;
      }
      case 'enqueue_job': {
        if (!String(action.handler ?? '').trim()) {
          errors.push(`${label}: Handler is required`);
        }
        if (typeof action.payload === 'string' && action.payload.trim()) {
          tryParseJsonField(action.payload, `${label}: Payload`, errors);
        }
        break;
      }
      default:
        break;
    }
  });

  if (errors.length > 0) return { ok: false, errors };
  return { ok: true };
}

/** Convert form state → API request payload (throws if invalid JSON after validate). */
export function formToPayload(form: HookFormState): CreateHookRequest {
  const trigger: HookTrigger =
    form.triggerType === 'event'
      ? {
          type: 'event',
          event: form.event,
          ...(isRecordEvent(form.event) && form.collection.trim()
            ? { collection: form.collection.trim() }
            : {}),
        }
      : { type: 'manual' };

  const actions = form.actions.map((a) => {
    const parsed: HookAction = { ...a };
    for (const key of ['headers', 'data', 'payload'] as const) {
      const raw = parsed[key];
      if (typeof raw === 'string' && raw.trim()) {
        try {
          parsed[key] = JSON.parse(raw.trim());
        } catch {
          // validateHookForm should catch this; leave as string only if somehow called without validation
          throw new Error(`Invalid JSON in action field "${key}"`);
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
    trigger,
    // Always send condition (including '') so PATCH can clear a previously set value
    // (backend: condition is not None → '' becomes null). Omitting the field leaves it unchanged.
    condition: form.condition.trim(),
    actions,
    enabled: form.enabled,
  };
}

/** Convert an existing Hook → form state */
export function hookToForm(
  hook: Pick<Hook, 'name' | 'description' | 'trigger' | 'condition' | 'actions' | 'enabled'>,
): HookFormState {
  const triggerType = hook.trigger.type === 'manual' ? 'manual' : 'event';

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

export function moveAction(
  actions: HookAction[],
  index: number,
  direction: -1 | 1,
): HookAction[] {
  const next = index + direction;
  if (next < 0 || next >= actions.length) return actions;
  const copy = [...actions];
  const tmp = copy[index];
  copy[index] = copy[next];
  copy[next] = tmp;
  return copy;
}

export function removeActionAt(
  actions: HookAction[],
  index: number,
): { actions: HookAction[]; selectedIndex: number | null } {
  const next = actions.filter((_, i) => i !== index);
  if (next.length === 0) return { actions: next, selectedIndex: null };
  if (index >= next.length) return { actions: next, selectedIndex: next.length - 1 };
  return { actions: next, selectedIndex: index };
}
