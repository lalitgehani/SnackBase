import { describe, it, expect, vi, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { hooksService } from '../hooks.service';

describe('hooksService.list', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches event and manual with trigger_type filters when no trigger_type param', async () => {
    server.use(
      http.get('http://localhost/api/v1/hooks', ({ request }) => {
        const url = new URL(request.url);
        const triggerType = url.searchParams.get('trigger_type');
        if (triggerType === 'event') {
          return HttpResponse.json({
            items: [
              {
                id: 'e1',
                name: 'Event',
                trigger: { type: 'event', event: 'records.create' },
                updated_at: '2026-01-02T00:00:00Z',
                actions: [],
                enabled: true,
              },
            ],
            total: 1,
          });
        }
        if (triggerType === 'manual') {
          return HttpResponse.json({
            items: [
              {
                id: 'm1',
                name: 'Manual',
                trigger: { type: 'manual' },
                updated_at: '2026-01-03T00:00:00Z',
                actions: [],
                enabled: true,
              },
            ],
            total: 1,
          });
        }
        return HttpResponse.json({ items: [], total: 0 });
      }),
    );

    const result = await hooksService.list();

    expect(result.items).toHaveLength(2);
    expect(result.total).toBe(2);
    expect(result.items.map((h) => h.id).sort()).toEqual(['e1', 'm1']);
  });

  it('passes explicit trigger_type for single filtered request', async () => {
    server.use(
      http.get('http://localhost/api/v1/hooks', ({ request }) => {
        const url = new URL(request.url);
        expect(url.searchParams.get('trigger_type')).toBe('event');
        return HttpResponse.json({ items: [], total: 0 });
      }),
    );

    await hooksService.list({ trigger_type: 'event' });
  });
});

describe('HookExecution type surface', () => {
  it('listExecutions returns data that may include execution_context', async () => {
    server.use(
      http.get('http://localhost/api/v1/hooks/h1/executions', () =>
        HttpResponse.json({
          items: [
            {
              id: 'ex1',
              hook_id: 'h1',
              trigger_type: 'manual',
              status: 'success',
              actions_executed: 1,
              error_message: null,
              duration_ms: 10,
              executed_at: '2026-01-01T00:00:00Z',
              execution_context: { foo: 'bar' },
            },
          ],
          total: 1,
        }),
      ),
    );

    const result = await hooksService.listExecutions('h1');
    expect(result.items[0].execution_context).toEqual({ foo: 'bar' });
  });
});
