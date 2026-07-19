/**
 * Bidirectional mapping between backend workflow steps and React Flow graph state.
 *
 * Node identity: React Flow node `id` equals step `name` for steps.
 * Trigger uses fixed id TRIGGER_NODE_ID and is never serialized into steps[].
 *
 * Control flow is rebuilt exclusively from edges → next / on_true / on_false.
 */

import type { Edge, Node } from '@xyflow/react';
import type { WorkflowStep, WorkflowTriggerConfig } from '@/services/workflows.service';
import {
    DEFAULT_TRIGGER_POSITION,
    TRIGGER_NODE_ID,
} from '../workflowConstants';
import { decorateEdge } from './connectionRules';

export interface FlowGraph {
    nodes: Node[];
    edges: Edge[];
}

/** Step payload stored on each RF step node. */
export interface StepNodeData extends Record<string, unknown> {
    kind: 'step';
    label: string;
    step: WorkflowStep;
    /** Graph/field validation severity for node badge (Phase 3). */
    issueSeverity?: 'error' | 'warning' | null;
}

/** Trigger payload stored on the single trigger node. */
export interface TriggerNodeData extends Record<string, unknown> {
    kind: 'trigger';
    label: string;
    trigger: WorkflowTriggerConfig;
    issueSeverity?: 'error' | 'warning' | null;
}

export type WorkflowNodeData = StepNodeData | TriggerNodeData;

const CONTROL_FLOW_KEYS = new Set(['next', 'on_true', 'on_false', 'position_x', 'position_y']);

function asNumber(value: unknown, fallback = 0): number {
    return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

export function isTriggerNode(node: Node): boolean {
    return node.id === TRIGGER_NODE_ID || node.type === 'trigger';
}

export function isStepNodeData(data: unknown): data is StepNodeData {
    return (
        typeof data === 'object' &&
        data !== null &&
        (data as StepNodeData).kind === 'step' &&
        typeof (data as StepNodeData).step === 'object'
    );
}

export function isTriggerNodeData(data: unknown): data is TriggerNodeData {
    return (
        typeof data === 'object' &&
        data !== null &&
        (data as TriggerNodeData).kind === 'trigger' &&
        typeof (data as TriggerNodeData).trigger === 'object'
    );
}

/** Human-readable subtitle for a trigger config. */
export function triggerSummary(trigger: WorkflowTriggerConfig): string {
    switch (trigger.type) {
        case 'event': {
            const parts = [trigger.event];
            if (trigger.collection) parts.push(trigger.collection);
            return `Event · ${parts.join(' · ')}`;
        }
        case 'schedule':
            return `Schedule · ${trigger.cron}`;
        case 'webhook':
            return 'Webhook';
        case 'manual':
        default:
            return 'Manual';
    }
}

function createTriggerNode(
    trigger: WorkflowTriggerConfig,
    position: { x: number; y: number } = DEFAULT_TRIGGER_POSITION,
): Node {
    return {
        id: TRIGGER_NODE_ID,
        type: 'trigger',
        position,
        deletable: false,
        data: {
            kind: 'trigger',
            label: 'Trigger',
            trigger,
        } satisfies TriggerNodeData,
    };
}

/**
 * Convert backend steps (+ optional trigger) to React Flow nodes/edges.
 * Always emits a trigger node when `trigger` is provided; defaults to manual.
 */
export function stepsToFlow(
    steps: WorkflowStep[],
    trigger?: WorkflowTriggerConfig | null,
): FlowGraph {
    const triggerConfig: WorkflowTriggerConfig = trigger ?? { type: 'manual' };

    // Place trigger left of first step when steps exist with positions
    let triggerPos = { ...DEFAULT_TRIGGER_POSITION };
    if (steps.length > 0) {
        const xs = steps.map((s) => asNumber(s.position_x, 0));
        const ys = steps.map((s) => asNumber(s.position_y, 0));
        const minX = Math.min(...xs);
        const avgY = ys.reduce((a, b) => a + b, 0) / ys.length;
        triggerPos = { x: minX - 220, y: avgY };
        if (!Number.isFinite(triggerPos.x)) triggerPos = { ...DEFAULT_TRIGGER_POSITION };
        if (!Number.isFinite(triggerPos.y)) triggerPos.y = DEFAULT_TRIGGER_POSITION.y;
    }

    const triggerNode = createTriggerNode(triggerConfig, triggerPos);

    const stepNodes: Node[] = steps.map((step, index) => {
        const name = step.name || `step_${index}`;
        const stepType = typeof step.type === 'string' && step.type ? step.type : 'action';
        return {
            id: name,
            type: stepType,
            position: {
                x: asNumber(step.position_x, 0),
                y: asNumber(step.position_y, 0),
            },
            data: {
                kind: 'step',
                label: name,
                step: { ...step, name, type: stepType },
            } satisfies StepNodeData,
        };
    });

    const edges: Edge[] = [];
    for (const step of steps) {
        const name = step.name;
        if (!name) continue;

        if (step.type === 'condition') {
            const onTrue = step.on_true;
            const onFalse = step.on_false;
            if (typeof onTrue === 'string' && onTrue) {
                edges.push({
                    id: `${name}->${onTrue}:true`,
                    source: name,
                    target: onTrue,
                    sourceHandle: 'true',
                    label: 'true',
                    type: 'smoothstep',
                });
            }
            if (typeof onFalse === 'string' && onFalse) {
                edges.push({
                    id: `${name}->${onFalse}:false`,
                    source: name,
                    target: onFalse,
                    sourceHandle: 'false',
                    label: 'false',
                    type: 'smoothstep',
                });
            }
            continue;
        }

        const next = step.next;
        if (typeof next === 'string' && next) {
            edges.push({
                id: `${name}->${next}`,
                source: name,
                target: next,
                type: 'smoothstep',
            });
        }
    }

    // Optional heuristic: if exactly one step has no inbound edges, connect trigger → that step
    const stepIds = new Set(stepNodes.map((n) => n.id));
    const inbound = new Set(edges.map((e) => e.target));
    const roots = [...stepIds].filter((id) => !inbound.has(id));
    if (roots.length === 1) {
        const root = roots[0];
        edges.unshift({
            id: `${TRIGGER_NODE_ID}->${root}`,
            source: TRIGGER_NODE_ID,
            target: root,
            type: 'smoothstep',
        });
    }

    const nodes = [triggerNode, ...stepNodes];
    const decorated = edges.map((e) => decorateEdge(e, nodes));

    return { nodes, edges: decorated };
}

/**
 * Seed graph for a new workflow (trigger only).
 */
export function createEmptyFlow(
    trigger: WorkflowTriggerConfig = { type: 'manual' },
): FlowGraph {
    return {
        nodes: [createTriggerNode(trigger)],
        edges: [],
    };
}

/**
 * Extract trigger config from the canvas trigger node.
 */
export function extractTriggerFromFlow(nodes: Node[]): WorkflowTriggerConfig {
    const t = nodes.find((n) => isTriggerNode(n));
    if (t && isTriggerNodeData(t.data)) {
        return t.data.trigger;
    }
    return { type: 'manual' };
}

/**
 * Convert React Flow state back to backend steps (excludes trigger).
 * Control flow is rebuilt exclusively from edges among step nodes.
 */
export function flowToSteps(nodes: Node[], edges: Edge[]): WorkflowStep[] {
    const stepNodes = nodes.filter((n) => !isTriggerNode(n));

    // Stable order: y then x
    const sorted = [...stepNodes].sort((a, b) => {
        const ay = a.position.y;
        const by = b.position.y;
        if (ay !== by) return ay - by;
        return a.position.x - b.position.x;
    });

    // Ignore edges from/to trigger for step control-flow fields
    const stepEdges = edges.filter(
        (e) => e.source !== TRIGGER_NODE_ID && e.target !== TRIGGER_NODE_ID,
    );

    const edgesBySource = new Map<string, Edge[]>();
    for (const edge of stepEdges) {
        if (edge.source === edge.target) continue;
        const list = edgesBySource.get(edge.source) ?? [];
        list.push(edge);
        edgesBySource.set(edge.source, list);
    }

    return sorted.map((node) => {
        const data = node.data as StepNodeData | undefined;
        const baseStep: WorkflowStep =
            data?.step && typeof data.step === 'object'
                ? { ...data.step }
                : {
                      type: (node.type as string) || 'action',
                      name: node.id,
                  };

        baseStep.name = node.id;
        if (!baseStep.type) {
            baseStep.type = (node.type as string) || 'action';
        }
        baseStep.position_x = node.position.x;
        baseStep.position_y = node.position.y;

        delete baseStep.next;
        delete baseStep.on_true;
        delete baseStep.on_false;

        const outgoing = edgesBySource.get(node.id) ?? [];
        if (baseStep.type === 'condition') {
            for (const edge of outgoing) {
                if (edge.sourceHandle === 'true') {
                    baseStep.on_true = edge.target;
                } else if (edge.sourceHandle === 'false') {
                    baseStep.on_false = edge.target;
                } else if (!baseStep.on_true) {
                    baseStep.on_true = edge.target;
                } else if (!baseStep.on_false) {
                    baseStep.on_false = edge.target;
                }
            }
        } else {
            const linear = outgoing.find((e) => !e.sourceHandle) ?? outgoing[0];
            if (linear) {
                baseStep.next = linear.target;
            }
        }

        for (const key of CONTROL_FLOW_KEYS) {
            if (key === 'position_x' || key === 'position_y') continue;
            if (baseStep[key] === undefined) {
                delete baseStep[key];
            }
        }

        return baseStep;
    });
}

/** Convenience for save: trigger + steps from canvas. */
export function flowToPayload(
    nodes: Node[],
    edges: Edge[],
): { trigger: WorkflowTriggerConfig; steps: WorkflowStep[] } {
    return {
        trigger: extractTriggerFromFlow(nodes),
        steps: flowToSteps(nodes, edges),
    };
}
