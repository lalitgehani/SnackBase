import { describe, it, expect } from 'vitest';
import type { WorkflowStep } from '@/services/workflows.service';
import {
    stepsToFlow,
    flowToSteps,
    extractTriggerFromFlow,
    createEmptyFlow,
    flowToPayload,
    isTriggerNode,
} from '../graphMapper';
import { TRIGGER_NODE_ID } from '../../workflowConstants';

describe('stepsToFlow / flowToSteps', () => {
    it('returns trigger-only graph for empty steps with default trigger', () => {
        const graph = stepsToFlow([]);
        expect(graph.nodes).toHaveLength(1);
        expect(isTriggerNode(graph.nodes[0])).toBe(true);
        expect(graph.edges).toEqual([]);
        expect(flowToSteps(graph.nodes, graph.edges)).toEqual([]);
        expect(extractTriggerFromFlow(graph.nodes)).toEqual({ type: 'manual' });
    });

    it('createEmptyFlow seeds manual trigger', () => {
        const graph = createEmptyFlow();
        expect(graph.nodes).toHaveLength(1);
        expect(graph.nodes[0].id).toBe(TRIGGER_NODE_ID);
        expect(extractTriggerFromFlow(graph.nodes)).toEqual({ type: 'manual' });
    });

    it('excludes trigger from steps[] but includes in payload', () => {
        const steps: WorkflowStep[] = [
            {
                type: 'action',
                name: 'a',
                action_type: 'send_webhook',
                config: {},
                position_x: 100,
                position_y: 0,
            },
        ];
        const graph = stepsToFlow(steps, { type: 'event', event: 'records.create' });
        expect(graph.nodes.some((n) => n.id === TRIGGER_NODE_ID)).toBe(true);
        const back = flowToSteps(graph.nodes, graph.edges);
        expect(back.every((s) => s.name !== TRIGGER_NODE_ID)).toBe(true);
        expect(back).toHaveLength(1);
        const payload = flowToPayload(graph.nodes, graph.edges);
        expect(payload.trigger).toEqual({ type: 'event', event: 'records.create' });
        expect(payload.steps).toHaveLength(1);
    });

    it('defaults missing positions to 0,0', () => {
        const steps: WorkflowStep[] = [
            { type: 'action', name: 'a', action_type: 'send_webhook', config: {} },
        ];
        const { nodes } = stepsToFlow(steps);
        const stepNode = nodes.find((n) => n.id === 'a')!;
        expect(stepNode.position).toEqual({ x: 0, y: 0 });
    });

    it('sets custom node type from step type', () => {
        const steps: WorkflowStep[] = [
            { type: 'condition', name: 'c', expression: 'x' },
            { type: 'wait_delay', name: 'w', duration: '1m' },
        ];
        const { nodes } = stepsToFlow(steps);
        expect(nodes.find((n) => n.id === 'c')?.type).toBe('condition');
        expect(nodes.find((n) => n.id === 'w')?.type).toBe('wait_delay');
        expect(nodes.find((n) => n.id === TRIGGER_NODE_ID)?.type).toBe('trigger');
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
        // trigger + 2 steps; edges: first→second + optional trigger→first (single root)
        const stepEdges = graph.edges.filter((e) => e.source !== TRIGGER_NODE_ID);
        expect(stepEdges).toHaveLength(1);
        expect(stepEdges[0]).toMatchObject({
            source: 'first',
            target: 'second',
        });
        expect(graph.nodes.find((n) => n.id === 'first')!.position).toEqual({ x: 10, y: 20 });

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
        const stepEdges = graph.edges.filter((e) => e.source !== TRIGGER_NODE_ID);
        expect(stepEdges).toHaveLength(2);
        const trueEdge = stepEdges.find((e) => e.sourceHandle === 'true');
        const falseEdge = stepEdges.find((e) => e.sourceHandle === 'false');
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

    it('does not serialize trigger→step edge into next', () => {
        const steps: WorkflowStep[] = [
            { type: 'action', name: 'only', action_type: 'send_webhook', config: {} },
        ];
        const graph = stepsToFlow(steps);
        // single root → trigger edge added
        expect(graph.edges.some((e) => e.source === TRIGGER_NODE_ID && e.target === 'only')).toBe(
            true,
        );
        const back = flowToSteps(graph.nodes, graph.edges);
        expect(back[0].next).toBeUndefined();
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

    it('omits step edges when next is missing', () => {
        const steps: WorkflowStep[] = [
            { type: 'action', name: 'lonely', action_type: 'send_webhook', config: {} },
        ];
        const graph = stepsToFlow(steps);
        const stepEdges = graph.edges.filter((e) => e.source !== TRIGGER_NODE_ID);
        expect(stepEdges).toHaveLength(0);
    });

    it('keeps orphan steps as nodes without edges', () => {
        const steps: WorkflowStep[] = [
            { type: 'action', name: 'a', action_type: 'send_webhook', config: {}, next: 'b' },
            { type: 'action', name: 'b', action_type: 'send_webhook', config: {} },
            { type: 'action', name: 'orphan', action_type: 'send_email', config: {} },
        ];
        const graph = stepsToFlow(steps);
        // trigger + 3 steps
        expect(graph.nodes).toHaveLength(4);
        const stepEdges = graph.edges.filter((e) => e.source !== TRIGGER_NODE_ID);
        expect(stepEdges).toHaveLength(1);
        expect(graph.nodes.map((n) => n.id).filter((id) => id !== TRIGGER_NODE_ID).sort()).toEqual([
            'a',
            'b',
            'orphan',
        ]);
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
        const idx = graph.nodes.findIndex((n) => n.id === 'n1');
        graph.nodes[idx] = {
            ...graph.nodes[idx],
            position: { x: 55.5, y: 99 },
        };
        const back = flowToSteps(graph.nodes, graph.edges);
        expect(back[0].position_x).toBe(55.5);
        expect(back[0].position_y).toBe(99);
    });

    it('round-trips full branched fixture with positions', () => {
        const steps: WorkflowStep[] = [
            {
                type: 'condition',
                name: 'gate',
                expression: 'status == "ok"',
                on_true: 'approve',
                on_false: 'reject',
                position_x: 200,
                position_y: 100,
            },
            {
                type: 'action',
                name: 'approve',
                action_type: 'send_webhook',
                config: { url: 'https://ok.example' },
                position_x: 420,
                position_y: 40,
            },
            {
                type: 'action',
                name: 'reject',
                action_type: 'send_email',
                config: { to: 'ops@example.com' },
                position_x: 420,
                position_y: 160,
            },
        ];
        const graph = stepsToFlow(steps, { type: 'manual' });
        expect(graph.nodes.find((n) => n.id === 'gate')!.position).toEqual({
            x: 200,
            y: 100,
        });
        const back = flowToSteps(graph.nodes, graph.edges);
        const gate = back.find((s) => s.name === 'gate')!;
        expect(gate).toMatchObject({
            type: 'condition',
            expression: 'status == "ok"',
            on_true: 'approve',
            on_false: 'reject',
            position_x: 200,
            position_y: 100,
        });
        expect(back.find((s) => s.name === 'approve')!.position_x).toBe(420);
        expect(back.find((s) => s.name === 'reject')!.position_y).toBe(160);
    });

    it('round-trips parallel multi-step branches with positions', () => {
        const steps: WorkflowStep[] = [
            {
                type: 'parallel',
                name: 'fanout',
                branches: [
                    ['left_a', 'left_b'],
                    ['right_a'],
                ],
                next: 'join',
                position_x: 100,
                position_y: 50,
            },
            {
                type: 'action',
                name: 'left_a',
                action_type: 'send_webhook',
                config: { url: 'https://l.a' },
                position_x: 250,
                position_y: 0,
            },
            {
                type: 'action',
                name: 'left_b',
                action_type: 'send_webhook',
                config: { url: 'https://l.b' },
                position_x: 400,
                position_y: 0,
            },
            {
                type: 'action',
                name: 'right_a',
                action_type: 'send_webhook',
                config: { url: 'https://r.a' },
                position_x: 250,
                position_y: 100,
            },
            {
                type: 'action',
                name: 'join',
                action_type: 'enqueue_job',
                config: { handler: 'done' },
                position_x: 550,
                position_y: 50,
            },
        ];
        const graph = stepsToFlow(steps);
        const back = flowToSteps(graph.nodes, graph.edges);
        const fan = back.find((s) => s.name === 'fanout')!;
        expect(fan.type).toBe('parallel');
        expect(fan.branches).toEqual([
            ['left_a', 'left_b'],
            ['right_a'],
        ]);
        expect(fan.next).toBe('join');
        expect(fan.position_x).toBe(100);
        expect(fan.position_y).toBe(50);
    });

    it('round-trips a 50-step linear graph with positions', () => {
        const steps: WorkflowStep[] = Array.from({ length: 50 }, (_, i) => ({
            type: 'action' as const,
            name: `step_${i + 1}`,
            action_type: 'send_webhook',
            config: { url: `https://example.com/${i}` },
            next: i < 49 ? `step_${i + 2}` : undefined,
            position_x: i * 40,
            position_y: (i % 5) * 20,
        }));
        const graph = stepsToFlow(steps);
        expect(graph.nodes.filter((n) => n.id !== TRIGGER_NODE_ID)).toHaveLength(50);
        const back = flowToSteps(graph.nodes, graph.edges);
        expect(back).toHaveLength(50);
        const byName = Object.fromEntries(back.map((s) => [s.name, s]));
        expect(byName.step_1.next).toBe('step_2');
        expect(byName.step_50.next).toBeUndefined();
        expect(byName.step_26.position_x).toBe(25 * 40);
        expect(byName.step_26.position_y).toBe((25 % 5) * 20);
    });
});
