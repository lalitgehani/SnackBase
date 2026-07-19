import { describe, it, expect } from 'vitest';
import {
  DEFAULT_FORM,
  formToPayload,
  hookToForm,
  moveAction,
  newAction,
  removeActionAt,
  validateHookForm,
  type HookFormState,
} from '../hookFormState';
import { HOOK_TEMPLATES } from '../templates/hookTemplates';

describe('hookFormState', () => {
  it('round-trips event hook form → payload → form', () => {
    const form: HookFormState = {
      name: 'Notify',
      description: 'desc',
      triggerType: 'event',
      event: 'records.create',
      collection: 'posts',
      condition: 'status == "active"',
      actions: [
        {
          type: 'send_webhook',
          url: 'https://example.com/hook',
          method: 'POST',
          headers: '{"X-A": "1"}',
          body_template: '{{record.id}}',
        },
        {
          type: 'create_record',
          collection: 'logs',
          data: '{"msg": "hi"}',
        },
      ],
      enabled: false,
    };

    const payload = formToPayload(form);
    expect(payload.name).toBe('Notify');
    expect(payload.description).toBe('desc');
    expect(payload.trigger).toEqual({
      type: 'event',
      event: 'records.create',
      collection: 'posts',
    });
    expect(payload.condition).toBe('status == "active"');
    expect(payload.enabled).toBe(false);
    expect(payload.actions).toHaveLength(2);
    expect(payload.actions?.[0]).toMatchObject({
      type: 'send_webhook',
      url: 'https://example.com/hook',
      headers: { 'X-A': '1' },
    });
    expect(payload.actions?.[1]).toMatchObject({
      type: 'create_record',
      data: { msg: 'hi' },
    });

    const back = hookToForm({
      name: payload.name,
      description: payload.description ?? null,
      trigger: payload.trigger,
      condition: payload.condition ?? null,
      actions: payload.actions ?? [],
      enabled: payload.enabled ?? true,
    });
    expect(back.triggerType).toBe('event');
    expect(back.event).toBe('records.create');
    expect(back.collection).toBe('posts');
    expect(back.actions).toHaveLength(2);
    expect(typeof back.actions[0].headers).toBe('string');
  });

  it('maps manual trigger correctly', () => {
    const form: HookFormState = {
      ...DEFAULT_FORM,
      name: 'Manual',
      triggerType: 'manual',
      actions: [newAction('enqueue_job')],
    };
    form.actions[0] = { ...form.actions[0], handler: 'do_work', payload: '{}' };
    const payload = formToPayload(form);
    expect(payload.trigger).toEqual({ type: 'manual' });
  });

  it('fails validation for empty name and empty actions', () => {
    const r = validateHookForm({ ...DEFAULT_FORM, name: '', actions: [] });
    expect(r.ok).toBe(false);
    if (!r.ok) {
      expect(r.errors.some((e) => e.includes('Name'))).toBe(true);
      expect(r.errors.some((e) => e.includes('action'))).toBe(true);
    }
  });

  it('fails validation for missing webhook URL', () => {
    const form: HookFormState = {
      ...DEFAULT_FORM,
      name: 'W',
      actions: [newAction('send_webhook')],
    };
    const r = validateHookForm(form);
    expect(r.ok).toBe(false);
    if (!r.ok) {
      expect(r.errors.some((e) => e.includes('URL'))).toBe(true);
    }
  });

  it('fails validation for invalid JSON headers', () => {
    const form: HookFormState = {
      ...DEFAULT_FORM,
      name: 'W',
      actions: [
        {
          type: 'send_webhook',
          url: 'https://x.com',
          method: 'POST',
          headers: '{not-json',
        },
      ],
    };
    const r = validateHookForm(form);
    expect(r.ok).toBe(false);
    if (!r.ok) {
      expect(r.errors.some((e) => e.toLowerCase().includes('json'))).toBe(true);
    }
  });

  it('moveAction reorders and removeActionAt adjusts selection', () => {
    const a = newAction('send_webhook');
    const b = newAction('send_email');
    const c = newAction('enqueue_job');
    const moved = moveAction([a, b, c], 0, 1);
    expect(moved[0].type).toBe('send_email');
    expect(moved[1].type).toBe('send_webhook');

    const { actions, selectedIndex } = removeActionAt([a, b, c], 2);
    expect(actions).toHaveLength(2);
    expect(selectedIndex).toBe(1);
  });

  it('each template builds form state', () => {
    for (const tpl of HOOK_TEMPLATES) {
      const form = tpl.build();
      expect(form).toBeDefined();
      expect(form.triggerType === 'event' || form.triggerType === 'manual').toBe(true);
      if (tpl.id === 'empty') {
        expect(form.actions).toHaveLength(0);
        expect(validateHookForm({ ...form, name: 'x' }).ok).toBe(false);
      } else {
        expect(form.actions.length).toBeGreaterThan(0);
        const withName = { ...form, name: form.name || tpl.name };
        // fix webhook URL if placeholder still present for notify
        if (tpl.id === 'notify-on-create') {
          expect(withName.triggerType).toBe('event');
          expect(withName.event).toBe('records.create');
          expect(withName.actions[0].type).toBe('send_webhook');
        }
        if (tpl.id === 'welcome-email') {
          expect(withName.event).toBe('auth.register');
          expect(withName.actions[0].type).toBe('send_email');
        }
        if (tpl.id === 'audit-log-write') {
          expect(withName.actions[0].type).toBe('create_record');
        }
      }
    }
  });

  it('sends empty-string condition so update can clear a previously set value', () => {
    const form: HookFormState = {
      ...DEFAULT_FORM,
      name: 'X',
      condition: '   ',
      actions: [{ type: 'send_webhook', url: 'https://x.com', method: 'POST' }],
    };
    const payload = formToPayload(form);
    // API contract: pass '' to clear (omit/undefined would leave existing condition)
    expect(payload.condition).toBe('');
    expect(Object.prototype.hasOwnProperty.call(payload, 'condition')).toBe(true);

    // Round-trip: hook with condition → form cleared → payload clears
    const existing = hookToForm({
      name: 'X',
      description: null,
      trigger: { type: 'manual' },
      condition: 'status == "active"',
      actions: [{ type: 'send_webhook', url: 'https://x.com', method: 'POST' }],
      enabled: true,
    });
    expect(existing.condition).toBe('status == "active"');
    const cleared = formToPayload({ ...existing, condition: '' });
    expect(cleared.condition).toBe('');
  });
});
