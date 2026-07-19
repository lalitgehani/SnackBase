import { describe, it, expect } from 'vitest';
import { buildReadonlyGraph, isReadonlyLockedNode } from '../buildReadonlyGraph';
import type { Workflow } from '@/services/workflows.service';
import { TRIGGER_NODE_ID } from '../../workflowConstants';

const baseWorkflow: Workflow = {
    id: 'wf-1',
    account_id: 'AB1234',
    name: 'Test',
    description: null,
    trigger_type: 'manual',
    trigger_config: { type: 'manual' },
    steps: [
        {
            type: 'action',
            name: 'step_a',
            action_type: 'send_webhook',
            config: {},
            next: 'step_b',
        },
        {
            type: 'action',
            name: 'step_b',
            action_type: 'send_email',
            config: {},
        },
    ],
    enabled: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    created_by: null,
};

describe('buildReadonlyGraph', () => {
    it('locks all nodes and preserves edges', () => {
        const { nodes, edges } = buildReadonlyGraph(baseWorkflow);
        expect(nodes.length).toBe(3); // trigger + 2 steps
        expect(nodes.every((n) => isReadonlyLockedNode(n))).toBe(true);
        expect(nodes.every((n) => (n.data as { locked?: boolean }).locked === true)).toBe(
            true,
        );
        expect(nodes.find((n) => n.id === TRIGGER_NODE_ID)).toBeTruthy();
        // trigger → step_a and step_a → step_b
        expect(edges.length).toBeGreaterThanOrEqual(1);
        expect(edges.some((e) => e.source === 'step_a' && e.target === 'step_b')).toBe(
            true,
        );
    });

    it('auto-layouts when all step positions are zero/missing', () => {
        const { nodes } = buildReadonlyGraph(baseWorkflow);
        const steps = nodes.filter((n) => n.id !== TRIGGER_NODE_ID);
        // After dagre layout, not all steps should remain stacked at 0,0
        const allZero = steps.every((n) => n.position.x === 0 && n.position.y === 0);
        expect(allZero).toBe(false);
    });

    it('keeps explicit positions when present', () => {
        const wf: Workflow = {
            ...baseWorkflow,
            steps: [
                {
                    type: 'action',
                    name: 'step_a',
                    action_type: 'send_webhook',
                    config: {},
                    next: 'step_b',
                    position_x: 120,
                    position_y: 40,
                },
                {
                    type: 'action',
                    name: 'step_b',
                    action_type: 'send_email',
                    config: {},
                    position_x: 400,
                    position_y: 80,
                },
            ],
        };
        const { nodes } = buildReadonlyGraph(wf);
        const a = nodes.find((n) => n.id === 'step_a')!;
        const b = nodes.find((n) => n.id === 'step_b')!;
        expect(a.position).toEqual({ x: 120, y: 40 });
        expect(b.position).toEqual({ x: 400, y: 80 });
    });

    it('preserves condition branch labels', () => {
        const wf: Workflow = {
            ...baseWorkflow,
            steps: [
                {
                    type: 'condition',
                    name: 'check',
                    expression: 'x > 1',
                    on_true: 'yes',
                    on_false: 'no',
                    position_x: 100,
                    position_y: 0,
                },
                {
                    type: 'action',
                    name: 'yes',
                    action_type: 'send_webhook',
                    config: {},
                    position_x: 300,
                    position_y: -40,
                },
                {
                    type: 'action',
                    name: 'no',
                    action_type: 'send_email',
                    config: {},
                    position_x: 300,
                    position_y: 40,
                },
            ],
        };
        const { edges } = buildReadonlyGraph(wf);
        const trueEdge = edges.find((e) => e.sourceHandle === 'true');
        const falseEdge = edges.find((e) => e.sourceHandle === 'false');
        expect(trueEdge?.label).toBeTruthy();
        expect(falseEdge?.label).toBeTruthy();
    });
});
