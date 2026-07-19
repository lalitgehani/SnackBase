import { describe, it, expect } from 'vitest';
import type { WorkflowStep } from '@/services/workflows.service';
import { stepsToFlow, flowToSteps } from '../graphMapper';

describe('stepsToFlow / flowToSteps', () => {
    it('returns empty graph for empty steps', () => {
        const graph = stepsToFlow([]);
        expect(graph.nodes).toEqual([]);
        expect(graph.edges).toEqual([]);
        expect(flowToSteps([], [])).toEqual([]);
    });

    it('defaults missing positions to 0,0', () => {
        const steps: WorkflowStep[] = [
            { type: 'action', name: 'a', action_type: 'send_webhook', config: {} },
        ];
        const { nodes } = stepsToFlow(steps);
        expect(nodes[0].position).toEqual({ x: 0, y: 0 });
    });

    it('round-trips action next and positions', () => {
        const steps: WorkflowStep[] = [
            {
                type: 'action',
                name: 'first',
                action_type: 'send_webhook',
                config: { url: 'https://a.com' },
                next: 'second',
                position_x: 10,
                position_y: 20,
            },
            {
                type: 'action',
                name: 'second',
                action_type: 'send_email',
                config: { to: 'x@y.com' },
                position_x: 200,
                position_y: 20,
            },
        ];

        const graph = stepsToFlow(steps);
        expect(graph.nodes).toHaveLength(2);
        expect(graph.edges).toHaveLength(1);
        expect(graph.edges[0]).toMatchObject({
            source: 'first',
            target: 'second',
        });
        expect(graph.nodes[0].position).toEqual({ x: 10, y: 20 });

        const back = flowToSteps(graph.nodes, graph.edges);
        expect(back).toHaveLength(2);
        const first = back.find((s) => s.name === 'first')!;
        const second = back.find((s) => s.name === 'second')!;
        expect(first.next).toBe('second');
        expect(first.position_x).toBe(10);
        expect(first.position_y).toBe(20);
        expect(first.action_type).toBe('send_webhook');
        expect(first.config).toEqual({ url: 'https://a.com' });
        expect(second.next).toBeUndefined();
        expect(second.position_x).toBe(200);
    });

    it('maps condition dual edges to on_true / on_false with handles', () => {
        const steps: WorkflowStep[] = [
            {
                type: 'condition',
                name: 'check',
                expression: 'status == "ok"',
                on_true: 'yes',
                on_false: 'no',
                position_x: 0,
                position_y: 0,
            },
            {
                type: 'action',
                name: 'yes',
                action_type: 'send_webhook',
                config: {},
                position_x: 100,
                position_y: -50,
            },
            {
                type: 'action',
                name: 'no',
                action_type: 'send_webhook',
                config: {},
                position_x: 100,
                position_y: 50,
            },
        ];

        const graph = stepsToFlow(steps);
        expect(graph.edges).toHaveLength(2);
        const trueEdge = graph.edges.find((e) => e.sourceHandle === 'true');
        const falseEdge = graph.edges.find((e) => e.sourceHandle === 'false');
        expect(trueEdge).toMatchObject({ source: 'check', target: 'yes' });
        expect(falseEdge).toMatchObject({ source: 'check', target: 'no' });

        const back = flowToSteps(graph.nodes, graph.edges);
        const check = back.find((s) => s.name === 'check')!;
        expect(check.type).toBe('condition');
        expect(check.on_true).toBe('yes');
        expect(check.on_false).toBe('no');
        expect(check.expression).toBe('status == "ok"');
        expect(check.next).toBeUndefined();
    });

    it('preserves wait_delay, loop, and parallel type fields', () => {
        const steps: WorkflowStep[] = [
            {
                type: 'wait_delay',
                name: 'pause',
                duration: '5m',
                next: 'loop_it',
                position_x: 0,
                position_y: 0,
            },
            {
                type: 'loop',
                name: 'loop_it',
                items: '{{trigger.records}}',
                step: 'inner',
                next: 'par',
                position_x: 100,
                position_y: 0,
            },
            {
                type: 'action',
                name: 'inner',
                action_type: 'send_webhook',
                config: {},
                position_x: 100,
                position_y: 100,
            },
            {
                type: 'parallel',
                name: 'par',
                branches: [['a'], ['b']],
                position_x: 200,
                position_y: 0,
            },
            {
                type: 'action',
                name: 'a',
                action_type: 'send_webhook',
                config: {},
                position_x: 300,
                position_y: -40,
            },
            {
                type: 'action',
                name: 'b',
                action_type: 'send_webhook',
                config: {},
                position_x: 300,
                position_y: 40,
            },
        ];

        const graph = stepsToFlow(steps);
        const back = flowToSteps(graph.nodes, graph.edges);

        expect(back.find((s) => s.name === 'pause')).toMatchObject({
            type: 'wait_delay',
            duration: '5m',
            next: 'loop_it',
        });
        expect(back.find((s) => s.name === 'loop_it')).toMatchObject({
            type: 'loop',
            items: '{{trigger.records}}',
            step: 'inner',
            next: 'par',
        });
        expect(back.find((s) => s.name === 'par')).toMatchObject({
            type: 'parallel',
            branches: [['a'], ['b']],
        });
    });

    it('omits edges when next is missing', () => {
        const steps: WorkflowStep[] = [
            { type: 'action', name: 'lonely', action_type: 'send_webhook', config: {} },
        ];
        const graph = stepsToFlow(steps);
        expect(graph.edges).toHaveLength(0);
    });

    it('keeps orphan steps as nodes without edges', () => {
        const steps: WorkflowStep[] = [
            { type: 'action', name: 'a', action_type: 'send_webhook', config: {}, next: 'b' },
            { type: 'action', name: 'b', action_type: 'send_webhook', config: {} },
            { type: 'action', name: 'orphan', action_type: 'send_email', config: {} },
        ];
        const graph = stepsToFlow(steps);
        expect(graph.nodes).toHaveLength(3);
        expect(graph.edges).toHaveLength(1);
        expect(graph.nodes.map((n) => n.id).sort()).toEqual(['a', 'b', 'orphan']);
        const back = flowToSteps(graph.nodes, graph.edges);
        expect(back.find((s) => s.name === 'orphan')?.next).toBeUndefined();
    });

    it('skips self-edges when converting flow to steps', () => {
        const steps: WorkflowStep[] = [
            { type: 'action', name: 'loop_bad', action_type: 'send_webhook', config: {} },
        ];
        const graph = stepsToFlow(steps);
        graph.edges.push({
            id: 'self',
            source: 'loop_bad',
            target: 'loop_bad',
        });
        const back = flowToSteps(graph.nodes, graph.edges);
        expect(back[0].next).toBeUndefined();
    });

    it('persists updated positions after node drag simulation', () => {
        const steps: WorkflowStep[] = [
            {
                type: 'action',
                name: 'n1',
                action_type: 'send_webhook',
                config: {},
                position_x: 0,
                position_y: 0,
            },
        ];
        const graph = stepsToFlow(steps);
        graph.nodes[0] = {
            ...graph.nodes[0],
            position: { x: 55.5, y: 99 },
        };
        const back = flowToSteps(graph.nodes, graph.edges);
        expect(back[0].position_x).toBe(55.5);
        expect(back[0].position_y).toBe(99);
    });
});
