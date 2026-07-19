import { describe, it, expect } from 'vitest';
import type { WorkflowStepLog } from '@/services/workflows.service';
import {
    normalizeLogStatus,
    latestLogsByStepName,
    mapStepLogsToNodeStatus,
    applyRunStatusToNodes,
    getLogForNode,
} from '../runStatusMapper';
import { TRIGGER_NODE_ID } from '../../workflowConstants';

function log(
    partial: Partial<WorkflowStepLog> & { step_name: string; status: string },
): WorkflowStepLog {
    return {
        id: partial.id ?? `log-${partial.step_name}`,
        instance_id: 'inst-1',
        workflow_id: 'wf-1',
        account_id: 'AB1234',
        step_type: partial.step_type ?? 'action',
        input: partial.input ?? null,
        output: partial.output ?? null,
        error_message: partial.error_message ?? null,
        started_at: partial.started_at ?? '2026-01-01T00:00:00Z',
        completed_at: partial.completed_at ?? '2026-01-01T00:00:01Z',
        ...partial,
    };
}

describe('normalizeLogStatus', () => {
    it('maps success to completed', () => {
        expect(normalizeLogStatus('success')).toBe('completed');
        expect(normalizeLogStatus('completed')).toBe('completed');
    });

    it('maps failed and skipped', () => {
        expect(normalizeLogStatus('failed')).toBe('failed');
        expect(normalizeLogStatus('skipped')).toBe('skipped');
    });
});

describe('latestLogsByStepName', () => {
    it('keeps the latest log per step by completed_at', () => {
        const logs = [
            log({
                step_name: 'a',
                status: 'failed',
                completed_at: '2026-01-01T00:00:01Z',
            }),
            log({
                id: 'log-a-2',
                step_name: 'a',
                status: 'success',
                completed_at: '2026-01-01T00:00:05Z',
            }),
            log({
                step_name: 'b',
                status: 'skipped',
                completed_at: '2026-01-01T00:00:02Z',
            }),
        ];
        const map = latestLogsByStepName(logs);
        expect(map.get('a')?.status).toBe('success');
        expect(map.get('b')?.status).toBe('skipped');
        expect(map.size).toBe(2);
    });
});

describe('mapStepLogsToNodeStatus', () => {
    it('returns empty map for no logs', () => {
        const map = mapStepLogsToNodeStatus([], {
            status: 'pending',
            current_step: null,
        });
        expect(map.size).toBe(0);
    });

    it('normalizes success to completed', () => {
        const map = mapStepLogsToNodeStatus(
            [log({ step_name: 'send', status: 'success' })],
            { status: 'completed', current_step: null },
        );
        expect(map.get('send')).toBe('completed');
    });

    it('overrides current_step when instance is running', () => {
        const map = mapStepLogsToNodeStatus(
            [log({ step_name: 'a', status: 'success' })],
            { status: 'running', current_step: 'b' },
        );
        expect(map.get('a')).toBe('completed');
        expect(map.get('b')).toBe('running');
    });

    it('overrides current_step when instance is waiting', () => {
        const map = mapStepLogsToNodeStatus(
            [log({ step_name: 'delay', status: 'success' })],
            { status: 'waiting', current_step: 'delay' },
        );
        expect(map.get('delay')).toBe('waiting');
    });

    it('marks failed steps', () => {
        const map = mapStepLogsToNodeStatus(
            [
                log({ step_name: 'a', status: 'success' }),
                log({
                    step_name: 'b',
                    status: 'failed',
                    error_message: 'boom',
                }),
            ],
            { status: 'failed', current_step: 'b' },
        );
        expect(map.get('b')).toBe('failed');
    });
});

describe('applyRunStatusToNodes', () => {
    it('marks missing steps pending and trigger completed when logs exist', () => {
        const nodes = [
            {
                id: TRIGGER_NODE_ID,
                type: 'trigger',
                position: { x: 0, y: 0 },
                data: {
                    kind: 'trigger' as const,
                    label: 'Trigger',
                    trigger: { type: 'manual' as const },
                },
            },
            {
                id: 'a',
                type: 'action',
                position: { x: 100, y: 0 },
                data: {
                    kind: 'step' as const,
                    label: 'a',
                    step: { type: 'action', name: 'a', action_type: 'send_webhook' },
                },
            },
            {
                id: 'b',
                type: 'action',
                position: { x: 200, y: 0 },
                data: {
                    kind: 'step' as const,
                    label: 'b',
                    step: { type: 'action', name: 'b', action_type: 'send_webhook' },
                },
            },
        ];
        const status = new Map([['a', 'completed' as const]]);
        const next = applyRunStatusToNodes(nodes, status);
        expect((next[0].data as { runStatus?: string }).runStatus).toBe('completed');
        expect((next[1].data as { runStatus?: string }).runStatus).toBe('completed');
        expect((next[2].data as { runStatus?: string }).runStatus).toBe('pending');
    });

    it('leaves trigger without status when no logs', () => {
        const nodes = [
            {
                id: TRIGGER_NODE_ID,
                type: 'trigger',
                position: { x: 0, y: 0 },
                data: {
                    kind: 'trigger' as const,
                    label: 'Trigger',
                    trigger: { type: 'manual' as const },
                },
            },
        ];
        const next = applyRunStatusToNodes(nodes, new Map());
        expect((next[0].data as { runStatus?: string | null }).runStatus).toBeNull();
    });
});

describe('getLogForNode', () => {
    it('returns null for trigger and missing steps', () => {
        const logs = [log({ step_name: 'a', status: 'success' })];
        expect(getLogForNode(logs, TRIGGER_NODE_ID)).toBeNull();
        expect(getLogForNode(logs, 'missing')).toBeNull();
        expect(getLogForNode(logs, 'a')?.step_name).toBe('a');
    });
});
