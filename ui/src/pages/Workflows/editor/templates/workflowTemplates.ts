/**
 * Client-side workflow templates for the create flow (Phase 3).
 * Fixtures hydrate React Flow nodes/edges before first save.
 */

import type { Edge, Node } from '@xyflow/react';
import type { WorkflowStep, WorkflowTriggerConfig } from '@/services/workflows.service';
import { stepsToFlow, type FlowGraph } from '../graphMapper';
import { layoutGraph } from '../autoLayout';

export interface WorkflowTemplateMeta {
    id: string;
    name: string;
    description: string;
    /** Approximate canvas node count including trigger. */
    nodeCount: number;
    suggestedName?: string;
    suggestedDescription?: string;
}

export interface WorkflowTemplate extends WorkflowTemplateMeta {
    build: () => FlowGraph & {
        suggestedName?: string;
        suggestedDescription?: string;
    };
}

function withLayout(graph: FlowGraph): FlowGraph {
    return {
        nodes: layoutGraph(graph.nodes, graph.edges),
        edges: graph.edges,
    };
}

function fromSteps(
    steps: WorkflowStep[],
    trigger: WorkflowTriggerConfig,
): FlowGraph {
    return withLayout(stepsToFlow(steps, trigger));
}

const emptyTemplate: WorkflowTemplate = {
    id: 'empty',
    name: 'Empty canvas',
    description: 'Start with a trigger only and build your own graph.',
    nodeCount: 1,
    suggestedName: '',
    build: () => {
        const graph = stepsToFlow([], { type: 'manual' });
        return {
            ...graph,
            suggestedName: '',
            suggestedDescription: '',
        };
    },
};

const recordLifecycle: WorkflowTemplate = {
    id: 'record-lifecycle',
    name: 'Record lifecycle',
    description: 'On record create, branch on a condition and notify via webhook or email.',
    nodeCount: 4,
    suggestedName: 'Record lifecycle',
    suggestedDescription: 'Notify when a new record is created',
    build: () => {
        const steps: WorkflowStep[] = [
            {
                type: 'condition',
                name: 'check_status',
                expression: 'record.status == "active"',
                on_true: 'notify_webhook',
                on_false: 'notify_email',
                position_x: 0,
                position_y: 0,
            },
            {
                type: 'action',
                name: 'notify_webhook',
                action_type: 'send_webhook',
                config: {
                    url: 'https://example.com/hooks/record-created',
                    method: 'POST',
                },
                position_x: 0,
                position_y: 0,
            },
            {
                type: 'action',
                name: 'notify_email',
                action_type: 'send_email',
                config: {
                    to: 'ops@example.com',
                    subject: 'New record created',
                    body: 'A new record was created and did not match the active branch.',
                },
                position_x: 0,
                position_y: 0,
            },
        ];
        const graph = fromSteps(steps, {
            type: 'event',
            event: 'records.create',
        });
        return {
            ...graph,
            suggestedName: 'Record lifecycle',
            suggestedDescription: 'Notify when a new record is created',
        };
    },
};

const scheduledJob: WorkflowTemplate = {
    id: 'scheduled-job',
    name: 'Scheduled job',
    description: 'Run on a cron schedule and enqueue a background job.',
    nodeCount: 2,
    suggestedName: 'Scheduled job',
    suggestedDescription: 'Daily job at 09:00',
    build: () => {
        const steps: WorkflowStep[] = [
            {
                type: 'action',
                name: 'enqueue_daily',
                action_type: 'enqueue_job',
                config: {
                    handler: 'jobs.daily_report',
                    payload: {},
                },
                position_x: 0,
                position_y: 0,
            },
        ];
        const graph = fromSteps(steps, {
            type: 'schedule',
            cron: '0 9 * * *',
        });
        return {
            ...graph,
            suggestedName: 'Scheduled job',
            suggestedDescription: 'Daily job at 09:00',
        };
    },
};

const waitForEvent: WorkflowTemplate = {
    id: 'wait-for-event',
    name: 'Wait for event',
    description: 'On record update, wait for a related event then call a webhook.',
    nodeCount: 3,
    suggestedName: 'Wait for event',
    suggestedDescription: 'Wait then notify after record update',
    build: () => {
        const steps: WorkflowStep[] = [
            {
                type: 'wait_event',
                name: 'wait_related',
                event: 'records.create',
                timeout: '24h',
                next: 'send_webhook',
                position_x: 0,
                position_y: 0,
            },
            {
                type: 'action',
                name: 'send_webhook',
                action_type: 'send_webhook',
                config: {
                    url: 'https://example.com/hooks/after-wait',
                    method: 'POST',
                },
                position_x: 0,
                position_y: 0,
            },
        ];
        const graph = fromSteps(steps, {
            type: 'event',
            event: 'records.update',
        });
        return {
            ...graph,
            suggestedName: 'Wait for event',
            suggestedDescription: 'Wait then notify after record update',
        };
    },
};

/** Ordered list for the template picker (Empty first). */
export const WORKFLOW_TEMPLATES: WorkflowTemplate[] = [
    emptyTemplate,
    recordLifecycle,
    scheduledJob,
    waitForEvent,
];

export function getTemplateById(id: string): WorkflowTemplate | undefined {
    return WORKFLOW_TEMPLATES.find((t) => t.id === id);
}

/** Apply template graph positions; re-export types for consumers. */
export type TemplateBuildResult = ReturnType<WorkflowTemplate['build']>;

/** Helper for tests: node type counts from a built graph. */
export function countNodesByType(nodes: Node[]): Record<string, number> {
    const counts: Record<string, number> = {};
    for (const n of nodes) {
        const t = n.type || 'unknown';
        counts[t] = (counts[t] ?? 0) + 1;
    }
    return counts;
}

export function countEdges(edges: Edge[]): number {
    return edges.length;
}
