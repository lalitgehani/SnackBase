import { describe, it, expect } from 'vitest';
import {
    generateUniqueStepName,
    createDefaultStep,
    parseActionConfigJson,
    renameNode,
    removeNodeAndEdges,
} from '../nodeDefaults';
import { TRIGGER_NODE_ID } from '../../workflowConstants';

describe('generateUniqueStepName', () => {
    it('starts at _1', () => {
        expect(generateUniqueStepName('action', [])).toBe('action_1');
    });

    it('skips existing names', () => {
        expect(generateUniqueStepName('action', ['action_1', 'action_2'])).toBe('action_3');
    });

    it('handles condition type', () => {
        expect(generateUniqueStepName('condition', ['condition_1'])).toBe('condition_2');
    });
});

describe('createDefaultStep', () => {
    it('creates action defaults', () => {
        expect(createDefaultStep('action', 'action_1')).toMatchObject({
            type: 'action',
            name: 'action_1',
            action_type: 'send_webhook',
            config: {},
        });
    });

    it('creates condition defaults', () => {
        expect(createDefaultStep('condition', 'c1')).toMatchObject({
            type: 'condition',
            name: 'c1',
            expression: '',
        });
    });

    it('creates parallel with empty branches', () => {
        expect(createDefaultStep('parallel', 'p1')).toMatchObject({
            type: 'parallel',
            branches: [],
        });
    });
});

describe('parseActionConfigJson', () => {
    it('accepts empty as {}', () => {
        expect(parseActionConfigJson('')).toEqual({ ok: true, value: {} });
    });

    it('parses object', () => {
        expect(parseActionConfigJson('{"url":"x"}')).toEqual({
            ok: true,
            value: { url: 'x' },
        });
    });

    it('rejects arrays', () => {
        expect(parseActionConfigJson('[]').ok).toBe(false);
    });

    it('rejects invalid JSON', () => {
        expect(parseActionConfigJson('{').ok).toBe(false);
    });
});

describe('renameNode', () => {
    it('rewrites id and edges', () => {
        const nodes = [
            {
                id: 'a',
                data: { kind: 'step', label: 'a', step: { type: 'action', name: 'a' } },
            },
            {
                id: 'b',
                data: { kind: 'step', label: 'b', step: { type: 'action', name: 'b' } },
            },
        ];
        const edges = [{ id: 'a->b', source: 'a', target: 'b' }];
        const result = renameNode(nodes, edges, 'a', 'alpha');
        expect(result.nodes.map((n) => n.id)).toEqual(['alpha', 'b']);
        expect(result.edges[0]).toMatchObject({ source: 'alpha', target: 'b' });
        expect((result.nodes[0].data as { step: { name: string } }).step.name).toBe('alpha');
    });

    it('rejects collision and trigger id', () => {
        const nodes = [
            { id: 'a', data: {} },
            { id: 'b', data: {} },
        ];
        const edges: { id: string; source: string; target: string }[] = [];
        expect(renameNode(nodes, edges, 'a', 'b').nodes[0].id).toBe('a');
        expect(renameNode(nodes, edges, 'a', TRIGGER_NODE_ID).nodes[0].id).toBe('a');
    });
});

describe('removeNodeAndEdges', () => {
    it('removes node and incident edges', () => {
        const nodes = [{ id: 'a' }, { id: 'b' }, { id: 'c' }];
        const edges = [
            { source: 'a', target: 'b' },
            { source: 'b', target: 'c' },
        ];
        const result = removeNodeAndEdges(nodes, edges, 'b');
        expect(result.nodes.map((n) => n.id)).toEqual(['a', 'c']);
        expect(result.edges).toHaveLength(0);
    });

    it('does not remove trigger', () => {
        const nodes = [{ id: TRIGGER_NODE_ID }, { id: 'a' }];
        const edges = [{ source: TRIGGER_NODE_ID, target: 'a' }];
        const result = removeNodeAndEdges(nodes, edges, TRIGGER_NODE_ID);
        expect(result.nodes).toHaveLength(2);
        expect(result.edges).toHaveLength(1);
    });
});
