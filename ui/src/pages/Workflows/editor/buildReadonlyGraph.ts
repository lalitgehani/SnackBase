/**
 * Build a locked, display-ready React Flow graph from a workflow definition.
 */

import type { Edge, Node } from '@xyflow/react';
import type { Workflow, WorkflowStep, WorkflowTriggerConfig } from '@/services/workflows.service';
import { stepsToFlow, type FlowGraph, type StepNodeData, type TriggerNodeData } from './graphMapper';
import { layoutGraph, shouldAutoLayoutOnLoad } from './autoLayout';

export interface BuildReadonlyGraphOptions {
    /** Force auto-layout even when positions exist. */
    forceLayout?: boolean;
}

function lockNode(node: Node): Node {
    const data = node.data as StepNodeData | TriggerNodeData | Record<string, unknown>;
    return {
        ...node,
        draggable: false,
        connectable: false,
        deletable: false,
        data: {
            ...data,
            locked: true,
        },
    };
}

/**
 * Convert workflow (or raw steps + trigger) to a read-only graph.
 * Applies LR auto-layout when all step positions are missing/zero.
 */
export function buildReadonlyGraph(
    workflowOrSteps: Workflow | WorkflowStep[],
    trigger?: WorkflowTriggerConfig | null,
    options: BuildReadonlyGraphOptions = {},
): FlowGraph {
    let steps: WorkflowStep[];
    let triggerConfig: WorkflowTriggerConfig | null | undefined;

    if (Array.isArray(workflowOrSteps)) {
        steps = workflowOrSteps;
        triggerConfig = trigger;
    } else {
        steps = workflowOrSteps.steps ?? [];
        triggerConfig = workflowOrSteps.trigger_config ?? trigger;
    }

    let { nodes, edges } = stepsToFlow(steps, triggerConfig);

    if (options.forceLayout || shouldAutoLayoutOnLoad(nodes)) {
        nodes = layoutGraph(nodes, edges);
    }

    return {
        nodes: nodes.map(lockNode),
        edges,
    };
}

/**
 * Apply lock flags to an existing graph (e.g. after status overlay).
 */
export function lockGraphNodes(nodes: Node[]): Node[] {
    return nodes.map(lockNode);
}

export function isReadonlyLockedNode(node: Node): boolean {
    const data = node.data as { locked?: boolean } | undefined;
    return data?.locked === true || node.draggable === false;
}
