import { describe, it, expect } from 'vitest';
import type { Edge, Node } from '@xyflow/react';
import { validateConnection, applyConnection } from '../connectionRules';
import { TRIGGER_NODE_ID } from '../../workflowConstants';

const nodes: Node[] = [
    {
        id: TRIGGER_NODE_ID,
        type: 'trigger',
        position: { x: 0, y: 0 },
        data: { kind: 'trigger', trigger: { type: 'manual' } },
    },
    {
        id: 'a',
        type: 'action',
        position: { x: 100, y: 0 },
        data: { kind: 'step', step: { type: 'action', name: 'a' } },
    },
    {
        id: 'b',
        type: 'action',
        position: { x: 200, y: 0 },
        data: { kind: 'step', step: { type: 'action', name: 'b' } },
    },
    {
        id: 'c',
        type: 'condition',
        position: { x: 100, y: 100 },
        data: { kind: 'step', step: { type: 'condition', name: 'c' } },
    },
];

describe('validateConnection', () => {
    it('rejects self connections', () => {
        expect(
            validateConnection({ source: 'a', target: 'a', sourceHandle: null, targetHandle: null }, nodes, [])
                .ok,
        ).toBe(false);
    });

    it('rejects connecting to trigger', () => {
        expect(
            validateConnection(
                { source: 'a', target: TRIGGER_NODE_ID, sourceHandle: null, targetHandle: null },
                nodes,
                [],
            ).ok,
        ).toBe(false);
    });

    it('allows trigger to step', () => {
        expect(
            validateConnection(
                { source: TRIGGER_NODE_ID, target: 'a', sourceHandle: null, targetHandle: null },
                nodes,
                [],
            ).ok,
        ).toBe(true);
    });

    it('rejects duplicates', () => {
        const edges: Edge[] = [{ id: '1', source: 'a', target: 'b' }];
        expect(
            validateConnection(
                { source: 'a', target: 'b', sourceHandle: null, targetHandle: null },
                nodes,
                edges,
            ).ok,
        ).toBe(false);
    });
});

describe('applyConnection', () => {
    it('creates edge and replaces existing next from same handle', () => {
        const edges: Edge[] = [{ id: 'a->b', source: 'a', target: 'b' }];
        const next = applyConnection(
            { source: 'a', target: 'c', sourceHandle: null, targetHandle: null },
            nodes,
            edges,
        );
        expect(next).not.toBeNull();
        expect(next!).toHaveLength(1);
        expect(next![0]).toMatchObject({ source: 'a', target: 'c' });
    });

    it('labels condition true/false edges', () => {
        const trueEdge = applyConnection(
            { source: 'c', target: 'a', sourceHandle: 'true', targetHandle: null },
            nodes,
            [],
        );
        expect(trueEdge![0]).toMatchObject({
            sourceHandle: 'true',
            label: 'true',
        });
        const falseEdge = applyConnection(
            { source: 'c', target: 'b', sourceHandle: 'false', targetHandle: null },
            nodes,
            trueEdge!,
        );
        expect(falseEdge).toHaveLength(2);
        expect(falseEdge!.find((e) => e.sourceHandle === 'false')?.label).toBe('false');
    });

    it('returns null for invalid', () => {
        expect(
            applyConnection(
                { source: 'a', target: 'a', sourceHandle: null, targetHandle: null },
                nodes,
                [],
            ),
        ).toBeNull();
    });
});
