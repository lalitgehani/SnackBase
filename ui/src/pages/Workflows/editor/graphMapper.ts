/**
 * Bidirectional mapping between backend workflow steps and React Flow graph state.
 *
 * Node identity: React Flow node `id` equals step `name`. Renames rewrite the id
 * and all edges that reference it (Phase 2 will surface rename UI).
 *
 * Trigger remains API-level fields in Phase 1; `trigger` is accepted for F2.1
 * compatibility but does not emit a canvas node yet.
 */

import type { Edge, Node } from '@xyflow/react';
import type { WorkflowStep, WorkflowTriggerConfig } from '@/services/workflows.service';

export interface FlowGraph {
    nodes: Node[];
    edges: Edge[];
}

/** Step payload stored on each RF node for round-trip fidelity. */
export interface StepNodeData extends Record<string, unknown> {
    label: string;
    step: WorkflowStep;
}

const CONTROL_FLOW_KEYS = new Set(['next', 'on_true', 'on_false', 'position_x', 'position_y']);

function asNumber(value: unknown, fallback = 0): number {
    return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

/**
 * Convert backend steps to React Flow nodes/edges.
 * Missing positions default to 0,0.
 */
export function stepsToFlow(
    steps: WorkflowStep[],
    _trigger?: WorkflowTriggerConfig | null,
): FlowGraph {
    const nodes: Node[] = steps.map((step, index) => {
        const name = step.name || `step_${index}`;
        return {
            id: name,
            position: {
                x: asNumber(step.position_x, 0),
                y: asNumber(step.position_y, 0),
            },
            data: {
                label: name,
                step: { ...step },
            } satisfies StepNodeData,
            // Default RF node type until Phase 2 custom cards
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
                });
            }
            if (typeof onFalse === 'string' && onFalse) {
                edges.push({
                    id: `${name}->${onFalse}:false`,
                    source: name,
                    target: onFalse,
                    sourceHandle: 'false',
                    label: 'false',
                });
            }
            // Condition steps may also have `next` in some legacy data; ignore if branches exist
            continue;
        }

        const next = step.next;
        if (typeof next === 'string' && next) {
            edges.push({
                id: `${name}->${next}`,
                source: name,
                target: next,
            });
        }
    }

    return { nodes, edges };
}

/**
 * Convert React Flow state back to backend steps.
 * Control flow is rebuilt exclusively from edges.
 * Positions are written as position_x / position_y.
 */
export function flowToSteps(nodes: Node[], edges: Edge[]): WorkflowStep[] {
    // Stable order: original index in data if present, else y then x
    const sorted = [...nodes].sort((a, b) => {
        const ay = a.position.y;
        const by = b.position.y;
        if (ay !== by) return ay - by;
        return a.position.x - b.position.x;
    });

    const edgesBySource = new Map<string, Edge[]>();
    for (const edge of edges) {
        if (edge.source === edge.target) {
            // Skip self-edges; validation surfaces them separately
            continue;
        }
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
                      type: 'action',
                      name: node.id,
                  };

        // Ensure name matches node id (canonical identity)
        baseStep.name = node.id;
        baseStep.position_x = node.position.x;
        baseStep.position_y = node.position.y;

        // Strip old control-flow keys then rebuild from edges
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
                    // Fallback: unlabeled first edge as true branch
                    baseStep.on_true = edge.target;
                } else if (!baseStep.on_false) {
                    baseStep.on_false = edge.target;
                }
            }
        } else {
            // Linear next: prefer single unlabeled edge; if multiple, first wins
            const linear = outgoing.find((e) => !e.sourceHandle) ?? outgoing[0];
            if (linear) {
                baseStep.next = linear.target;
            }
        }

        // Drop undefined control-flow leftovers that might confuse equality tests
        for (const key of CONTROL_FLOW_KEYS) {
            if (key === 'position_x' || key === 'position_y') continue;
            if (baseStep[key] === undefined) {
                delete baseStep[key];
            }
        }

        return baseStep;
    });
}
