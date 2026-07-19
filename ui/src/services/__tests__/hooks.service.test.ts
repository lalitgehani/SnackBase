import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient } from '@/lib/api';
import { hooksService } from '../hooks.service';

vi.mock('@/lib/api', () => ({
    apiClient: {
        get: vi.fn(),
        post: vi.fn(),
        patch: vi.fn(),
        delete: vi.fn(),
    },
}));

describe('hooksService.list', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('fetches event and manual with trigger_type filters when no trigger_type param', async () => {
        vi.mocked(apiClient.get)
            .mockResolvedValueOnce({
                data: {
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
                },
            })
            .mockResolvedValueOnce({
                data: {
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
                },
            });

        const result = await hooksService.list();

        expect(apiClient.get).toHaveBeenCalledTimes(2);
        const calls = vi.mocked(apiClient.get).mock.calls;
        const params = calls.map((c) => c[1]?.params);
        expect(params).toEqual(
            expect.arrayContaining([
                expect.objectContaining({ trigger_type: 'event' }),
                expect.objectContaining({ trigger_type: 'manual' }),
            ]),
        );
        // Never unfiltered dump
        for (const p of params) {
            expect(p?.trigger_type).toBeDefined();
            expect(p?.trigger_type).not.toBe('schedule');
        }
        expect(result.items.map((i) => i.id)).toEqual(['m1', 'e1']); // sorted by updated_at desc
        expect(result.total).toBe(2);
    });

    it('passes explicit trigger_type for single filtered request', async () => {
        vi.mocked(apiClient.get).mockResolvedValueOnce({
            data: { items: [], total: 0 },
        });

        await hooksService.list({ trigger_type: 'manual', limit: 50 });

        expect(apiClient.get).toHaveBeenCalledWith('/hooks', {
            params: expect.objectContaining({
                trigger_type: 'manual',
                limit: 50,
            }),
        });
        expect(apiClient.get).toHaveBeenCalledTimes(1);
    });
});

describe('HookExecution type surface', () => {
    it('listExecutions returns data that may include execution_context', async () => {
        vi.mocked(apiClient.get).mockResolvedValueOnce({
            data: {
                items: [
                    {
                        id: 'ex1',
                        hook_id: 'hk-1',
                        trigger_type: 'manual',
                        status: 'success',
                        actions_executed: 1,
                        error_message: null,
                        duration_ms: 12,
                        executed_at: '2026-01-01T00:00:00Z',
                        execution_context: { record: { id: 'r1' } },
                    },
                ],
                total: 1,
            },
        });

        const res = await hooksService.listExecutions('hk-1');
        expect(res.items[0].execution_context).toEqual({ record: { id: 'r1' } });
    });
});
