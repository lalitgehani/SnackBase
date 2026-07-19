import { describe, it, expect } from 'vitest';
import type { Edge, Node } from '@xyflow/react';
import { layoutGraph, shouldAutoLayoutOnLoad } from '../autoLayout';
import { TRIGGER_NODE_ID } from '../../workflowConstants';

function node(id: string, x = 0, y = 0, type = 'action'): Node {
    return {
        id,
        type,
        position: { x, y },
        data: { kind: id === TRIGGER_NODE_ID ? 'trigger' : 'step', label: id },
    };
}

describe('layoutGraph', () => {
    it('returns finite positions for N nodes', () => {
        const nodes: Node[] = [
            node(TRIGGER_NODE_ID, 0, 0, 'trigger'),
            node('a'),
            node('b'),
            node('c'),
        ];
        const edges: Edge[] = [
            { id: '1', source: TRIGGER_NODE_ID, target: 'a' },
            { id: '2', source: 'a', target: 'b' },
            { id: '3', source: 'b', target: 'c' },
        ];
        const laid = layoutGraph(nodes, edges);
        expect(laid).toHaveLength(4);
        for (const n of laid) {
            expect(Number.isFinite(n.position.x)).toBe(true);
            expect(Number.isFinite(n.position.y)).toBe(true);
        }
        // Edges unchanged by caller — layout only returns nodes
        expect(edges).toHaveLength(3);
    });

    it('is deterministic for the same graph', () => {
        const nodes: Node[] = [
            node(TRIGGER_NODE_ID, 0, 0, 'trigger'),
            node('a'),
            node('b'),
        ];
        const edges: Edge[] = [
            { id: '1', source: TRIGGER_NODE_ID, target: 'a' },
            { id: '2', source: 'a', target: 'b' },
        ];
        const a = layoutGraph(nodes, edges);
        const b = layoutGraph(nodes, edges);
        expect(a.map((n) => n.position)).toEqual(b.map((n) => n.position));
    });

    it('spreads nodes left-to-right for a chain', () => {
        const nodes: Node[] = [
            node(TRIGGER_NODE_ID, 0, 0, 'trigger'),
            node('a'),
            node('b'),
        ];
        const edges: Edge[] = [
            { id: '1', source: TRIGGER_NODE_ID, target: 'a' },
            { id: '2', source: 'a', target: 'b' },
        ];
        const laid = layoutGraph(nodes, edges, { direction: 'LR' });
        const byId = Object.fromEntries(laid.map((n) => [n.id, n.position]));
        expect(byId[TRIGGER_NODE_ID].x).toBeLessThan(byId.a.x);
        expect(byId.a.x).toBeLessThan(byId.b.x);
    });

    it('returns empty array for empty input', () => {
        expect(layoutGraph([], [])).toEqual([]);
    });

    it('layouts a 50-node linear chain with finite positions', () => {
        const nodes: Node[] = [node(TRIGGER_NODE_ID, 0, 0, 'trigger')];
        const edges: Edge[] = [];
        for (let i = 1; i <= 50; i++) {
            const id = `n${i}`;
            nodes.push(node(id));
            const prev = i === 1 ? TRIGGER_NODE_ID : `n${i - 1}`;
            edges.push({ id: `e${i}`, source: prev, target: id });
        }
        const laid = layoutGraph(nodes, edges);
        expect(laid).toHaveLength(51);
        for (const n of laid) {
            expect(Number.isFinite(n.position.x)).toBe(true);
            expect(Number.isFinite(n.position.y)).toBe(true);
        }
        const byId = Object.fromEntries(laid.map((n) => [n.id, n.position]));
        expect(byId.n1.x).toBeLessThan(byId.n50.x);
    });
});

describe('shouldAutoLayoutOnLoad', () => {
    it('is false for trigger-only', () => {
        expect(shouldAutoLayoutOnLoad([node(TRIGGER_NODE_ID, 0, 0, 'trigger')])).toBe(false);
    });

    it('is true when all steps are at origin', () => {
        expect(
            shouldAutoLayoutOnLoad([
                node(TRIGGER_NODE_ID, 10, 10, 'trigger'),
                node('a', 0, 0),
                node('b', 0, 0),
            ]),
        ).toBe(true);
    });

    it('is false when any step has non-zero position', () => {
        expect(
            shouldAutoLayoutOnLoad([
                node(TRIGGER_NODE_ID, 0, 0, 'trigger'),
                node('a', 100, 0),
            ]),
        ).toBe(false);
    });
});
