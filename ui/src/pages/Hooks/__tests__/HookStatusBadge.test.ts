import { describe, it, expect } from 'vitest';
import {
  actionSummary,
  formatDurationMs,
  formatHookDate,
  triggerSummary,
} from '../HookStatusBadge';

describe('HookStatusBadge helpers', () => {
  it('formatHookDate returns em dash for null', () => {
    expect(formatHookDate(null)).toBe('—');
    expect(formatHookDate(undefined)).toBe('—');
  });

  it('formatDurationMs formats and handles null', () => {
    expect(formatDurationMs(null)).toBe('—');
    expect(formatDurationMs(15)).toBe('15ms');
  });

  it('triggerSummary for event and manual', () => {
    expect(triggerSummary({ trigger: { type: 'manual' } })).toBe('Manual trigger');
    expect(
      triggerSummary({
        trigger: { type: 'event', event: 'records.create', collection: 'posts' },
      }),
    ).toBe('records.create on posts');
  });

  it('actionSummary covers action types', () => {
    expect(
      actionSummary({ type: 'send_webhook', url: 'https://example.com/hook' }),
    ).toContain('example.com');
    expect(actionSummary({ type: 'send_email', to: 'a@b.com' })).toContain('a@b.com');
    expect(actionSummary({ type: 'create_record', collection: 'logs' })).toContain('logs');
    expect(actionSummary({ type: 'enqueue_job', handler: 'work' })).toContain('work');
  });
});
