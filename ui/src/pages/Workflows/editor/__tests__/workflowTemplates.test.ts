import { describe, it, expect } from 'vitest';
import { flowToSteps } from '../graphMapper';
import {
    WORKFLOW_TEMPLATES,
    getTemplateById,
    countNodesByType,
} from '../templates/workflowTemplates';
import {
    validateWorkflowGraph,
    hasHardErrors,
    validateStepNames,
} from '../graphValidation';
import { TRIGGER_NODE_ID } from '../../workflowConstants';

describe('workflow templates', () => {
    it('includes Empty plus at least 3 non-empty templates', () => {
        expect(WORKFLOW_TEMPLATES.some((t) => t.id === 'empty')).toBe(true);
        const nonEmpty = WORKFLOW_TEMPLATES.filter((t) => t.id !== 'empty');
        expect(nonEmpty.length).toBeGreaterThanOrEqual(3);
    });

    it('each template builds a graph with a trigger', () => {
        for (const tpl of WORKFLOW_TEMPLATES) {
            const graph = tpl.build();
            expect(graph.nodes.some((n) => n.id === TRIGGER_NODE_ID)).toBe(true);
            expect(graph.nodes.length).toBe(tpl.nodeCount);
        }
    });

    it('maps each template to valid steps via flowToSteps', () => {
        for (const tpl of WORKFLOW_TEMPLATES) {
            const graph = tpl.build();
            const steps = flowToSteps(graph.nodes, graph.edges);
            expect(validateStepNames(steps)).toBeNull();
            // No trigger in steps
            expect(steps.every((s) => s.name !== TRIGGER_NODE_ID)).toBe(true);
        }
    });

    it('non-empty templates produce connected graphs without hard errors', () => {
        for (const tpl of WORKFLOW_TEMPLATES.filter((t) => t.id !== 'empty')) {
            const graph = tpl.build();
            const issues = validateWorkflowGraph(graph.nodes, graph.edges);
            expect(hasHardErrors(issues), `${tpl.id}: ${JSON.stringify(issues)}`).toBe(
                false,
            );
        }
    });

    it('record-lifecycle has trigger + condition + actions', () => {
        const tpl = getTemplateById('record-lifecycle');
        expect(tpl).toBeDefined();
        const graph = tpl!.build();
        const counts = countNodesByType(graph.nodes);
        expect(counts.trigger).toBe(1);
        expect(counts.condition).toBe(1);
        expect(counts.action).toBe(2);
        expect(graph.edges.length).toBeGreaterThanOrEqual(3);
    });

    it('scheduled-job has schedule trigger and enqueue action', () => {
        const tpl = getTemplateById('scheduled-job');
        const graph = tpl!.build();
        const trigger = graph.nodes.find((n) => n.id === TRIGGER_NODE_ID);
        expect((trigger?.data as { trigger?: { type?: string } })?.trigger?.type).toBe(
            'schedule',
        );
        const steps = flowToSteps(graph.nodes, graph.edges);
        expect(steps[0]?.action_type).toBe('enqueue_job');
    });

    it('wait-for-event has wait_event + action', () => {
        const tpl = getTemplateById('wait-for-event');
        const graph = tpl!.build();
        const counts = countNodesByType(graph.nodes);
        expect(counts.wait_event).toBe(1);
        expect(counts.action).toBe(1);
    });
});
