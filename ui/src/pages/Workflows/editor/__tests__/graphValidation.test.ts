import { describe, it, expect } from 'vitest';
import type { Edge, Node } from '@xyflow/react';
import type { WorkflowStep } from '@/services/workflows.service';
import {
    validateStepNames,
    hasSelfEdges,
    validateGraphEdges,
    validateWorkflowGraph,
    validateActionConfig,
    detectCycleNodeIds,
    hasHardErrors,
    nodeIssueSeverity,
} from '../graphValidation';
import { TRIGGER_NODE_ID } from '../../workflowConstants';

function triggerNode(): Node {
    return {
        id: TRIGGER_NODE_ID,
        type: 'trigger',
        position: { x: 0, y: 0 },
        data: { kind: 'trigger', label: 'Trigger', trigger: { type: 'manual' } },
    };
}

function stepNode(
    id: string,
    step: Partial<WorkflowStep> & { type: string },
): Node {
    return {
        id,
        type: step.type,
        position: { x: 0, y: 0 },
        data: {
            kind: 'step',
            label: id,
            step: { name: id, ...step },
        },
    };
}

describe('validateStepNames', () => {
    it('returns null for unique non-empty names', () => {
        const steps: WorkflowStep[] = [
            { type: 'action', name: 'a' },
            { type: 'action', name: 'b' },
        ];
        expect(validateStepNames(steps)).toBeNull();
    });

    it('returns null for empty steps list', () => {
        expect(validateStepNames([])).toBeNull();
    });

    it('rejects empty names', () => {
        const steps: WorkflowStep[] = [
            { type: 'action', name: 'a' },
            { type: 'action', name: '  ' },
        ];
        expect(validateStepNames(steps)).toBe('All steps must have a name');
    });

    it('rejects duplicates', () => {
        const steps: WorkflowStep[] = [
            { type: 'action', name: 'same' },
            { type: 'action', name: 'same' },
        ];
        expect(validateStepNames(steps)).toBe('Step names must be unique');
    });
});

describe('self-edges', () => {
    it('detects self-edges', () => {
        const edges: Edge[] = [
            { id: '1', source: 'a', target: 'b' },
            { id: '2', source: 'c', target: 'c' },
        ];
        expect(hasSelfEdges(edges)).toBe(true);
        expect(validateGraphEdges(edges)).toBe('Self-edges are not allowed');
    });

    it('passes when no self-edges', () => {
        const edges: Edge[] = [{ id: '1', source: 'a', target: 'b' }];
        expect(hasSelfEdges(edges)).toBe(false);
        expect(validateGraphEdges(edges)).toBeNull();
    });
});

describe('validateActionConfig', () => {
    it('requires action_type', () => {
        expect(validateActionConfig({ type: 'action', name: 'a' })).toMatch(/Action type/);
    });

    it('requires webhook url', () => {
        expect(
            validateActionConfig({
                type: 'action',
                name: 'a',
                action_type: 'send_webhook',
                config: {},
            }),
        ).toMatch(/url/);
    });

    it('passes complete webhook', () => {
        expect(
            validateActionConfig({
                type: 'action',
                name: 'a',
                action_type: 'send_webhook',
                config: { url: 'https://example.com' },
            }),
        ).toBeNull();
    });
});

describe('validateWorkflowGraph', () => {
    it('accepts valid linear trigger → action', () => {
        const nodes: Node[] = [
            triggerNode(),
            stepNode('notify', {
                type: 'action',
                action_type: 'send_webhook',
                config: { url: 'https://example.com' },
            }),
        ];
        const edges: Edge[] = [
            { id: 'e1', source: TRIGGER_NODE_ID, target: 'notify' },
        ];
        const issues = validateWorkflowGraph(nodes, edges);
        expect(hasHardErrors(issues)).toBe(false);
        expect(issues.filter((i) => i.severity === 'warning')).toHaveLength(0);
    });

    it('errors when trigger is missing', () => {
        const nodes: Node[] = [
            stepNode('a', {
                type: 'action',
                action_type: 'send_webhook',
                config: { url: 'https://x.com' },
            }),
        ];
        const issues = validateWorkflowGraph(nodes, []);
        expect(issues.some((i) => i.id === 'missing-trigger')).toBe(true);
        expect(hasHardErrors(issues)).toBe(true);
    });

    it('warns on orphan steps', () => {
        const nodes: Node[] = [
            triggerNode(),
            stepNode('orphan', {
                type: 'action',
                action_type: 'send_webhook',
                config: { url: 'https://x.com' },
            }),
        ];
        const issues = validateWorkflowGraph(nodes, []);
        expect(issues.some((i) => i.id === 'orphan-orphan' && i.severity === 'warning')).toBe(
            true,
        );
        expect(hasHardErrors(issues)).toBe(false);
    });

    it('warns when condition is missing a branch', () => {
        const nodes: Node[] = [
            triggerNode(),
            stepNode('cond', { type: 'condition', expression: 'true' }),
            stepNode('a', {
                type: 'action',
                action_type: 'send_webhook',
                config: { url: 'https://x.com' },
            }),
        ];
        const edges: Edge[] = [
            { id: 't', source: TRIGGER_NODE_ID, target: 'cond' },
            { id: 'e1', source: 'cond', target: 'a', sourceHandle: 'true' },
        ];
        const issues = validateWorkflowGraph(nodes, edges);
        expect(issues.some((i) => i.severity === 'warning' && i.message.includes('false'))).toBe(
            true,
        );
    });

    it('errors on cycles', () => {
        const nodes: Node[] = [
            triggerNode(),
            stepNode('a', {
                type: 'action',
                action_type: 'send_webhook',
                config: { url: 'https://x.com' },
            }),
            stepNode('b', {
                type: 'action',
                action_type: 'send_webhook',
                config: { url: 'https://y.com' },
            }),
        ];
        const edges: Edge[] = [
            { id: 't', source: TRIGGER_NODE_ID, target: 'a' },
            { id: 'ab', source: 'a', target: 'b' },
            { id: 'ba', source: 'b', target: 'a' },
        ];
        expect(detectCycleNodeIds(nodes, edges)).not.toBeNull();
        const issues = validateWorkflowGraph(nodes, edges);
        expect(issues.some((i) => i.id === 'cycle')).toBe(true);
        expect(hasHardErrors(issues)).toBe(true);
    });

    it('errors on missing webhook url', () => {
        const nodes: Node[] = [
            triggerNode(),
            stepNode('notify', {
                type: 'action',
                action_type: 'send_webhook',
                config: {},
            }),
        ];
        const edges: Edge[] = [
            { id: 'e1', source: TRIGGER_NODE_ID, target: 'notify' },
        ];
        const issues = validateWorkflowGraph(nodes, edges);
        expect(hasHardErrors(issues)).toBe(true);
        expect(nodeIssueSeverity(issues, 'notify')).toBe('error');
    });
});
