import { describe, it, expect } from 'vitest';
import type { Edge, Node } from '@xyflow/react';
import {
    validateConnection,
    applyConnection,
    getOutgoingTarget,
    setOutgoingTarget,
    defaultAutoConnectHandle,
} from '../connectionRules';
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

describe('getOutgoingTarget / setOutgoingTarget', () => {
    it('reads and clears default next edge', () => {
        const edges: Edge[] = [{ id: 'a->b', source: 'a', target: 'b' }];
        expect(getOutgoingTarget(edges, 'a')).toBe('b');
        expect(getOutgoingTarget(edges, 'a', null)).toBe('b');
        const cleared = setOutgoingTarget(nodes, edges, 'a', null);
        expect(getOutgoingTarget(cleared, 'a')).toBeNull();
    });

    it('sets next and replaces existing', () => {
        const edges: Edge[] = [{ id: 'a->b', source: 'a', target: 'b' }];
        const next = setOutgoingTarget(nodes, edges, 'a', 'c');
        expect(getOutgoingTarget(next, 'a')).toBe('c');
        expect(next.filter((e) => e.source === 'a')).toHaveLength(1);
    });

    it('sets condition true/false independently', () => {
        let edges: Edge[] = [];
        edges = setOutgoingTarget(nodes, edges, 'c', 'a', 'true');
        edges = setOutgoingTarget(nodes, edges, 'c', 'b', 'false');
        expect(getOutgoingTarget(edges, 'c', 'true')).toBe('a');
        expect(getOutgoingTarget(edges, 'c', 'false')).toBe('b');
        expect(edges.find((e) => e.sourceHandle === 'true')?.label).toBe('true');
        edges = setOutgoingTarget(nodes, edges, 'c', null, 'true');
        expect(getOutgoingTarget(edges, 'c', 'true')).toBeNull();
        expect(getOutgoingTarget(edges, 'c', 'false')).toBe('b');
    });
});

describe('defaultAutoConnectHandle', () => {
    it('returns true for condition sources', () => {
        expect(defaultAutoConnectHandle(nodes, 'c')).toBe('true');
    });

    it('returns undefined for action/trigger', () => {
        expect(defaultAutoConnectHandle(nodes, 'a')).toBeUndefined();
        expect(defaultAutoConnectHandle(nodes, TRIGGER_NODE_ID)).toBeUndefined();
    });
});
