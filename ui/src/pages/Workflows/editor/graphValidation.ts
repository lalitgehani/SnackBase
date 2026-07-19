/**
 * Graph validation for the workflow visual editor (Phase 3).
 * Pure functions — no React dependencies beyond RF node/edge types.
 */

import type { Edge, Node } from '@xyflow/react';
import type { WorkflowStep } from '@/services/workflows.service';
import { TRIGGER_NODE_ID } from '../workflowConstants';
import { isStepNodeData, isTriggerNode } from './graphMapper';

export type ValidationSeverity = 'error' | 'warning';

export interface ValidationIssue {
    id: string;
    severity: ValidationSeverity;
    message: string;
    /** React Flow node id (step name or trigger) when issue is node-scoped. */
    nodeId?: string;
}

/**
 * Required config keys per action_type (matches action_executor.py).
 */
export const ACTION_REQUIRED_CONFIG: Record<string, string[]> = {
    send_webhook: ['url'],
    send_email: ['to'],
    create_record: ['collection'],
    update_record: ['collection', 'record_id'],
    delete_record: ['collection', 'record_id'],
    enqueue_job: ['handler'],
};

/**
 * Validate step names are non-empty and unique.
 * @returns Error message or null if valid.
 */
export function validateStepNames(steps: WorkflowStep[]): string | null {
    const names = steps.map((s) => (s.name ?? '').trim());
    if (names.some((n) => !n)) {
        return 'All steps must have a name';
    }
    if (new Set(names).size !== names.length) {
        return 'Step names must be unique';
    }
    return null;
}

/** True if any edge connects a node to itself. */
export function hasSelfEdges(edges: Edge[]): boolean {
    return edges.some((e) => e.source === e.target);
}

/**
 * Collect self-edge issues for UI messaging.
 */
export function validateGraphEdges(edges: Edge[]): string | null {
    if (hasSelfEdges(edges)) {
        return 'Self-edges are not allowed';
    }
    return null;
}

function stepFromNode(node: Node): WorkflowStep | null {
    if (isTriggerNode(node)) return null;
    if (isStepNodeData(node.data)) {
        return { ...node.data.step, name: node.id };
    }
    return {
        type: (node.type as string) || 'action',
        name: node.id,
    };
}

function configIsObject(config: unknown): config is Record<string, unknown> {
    return config !== null && typeof config === 'object' && !Array.isArray(config);
}

/**
 * Validate a single action step's action_type + config required keys.
 */
export function validateActionConfig(step: WorkflowStep): string | null {
    if (step.type !== 'action') return null;
    const actionType = String(step.action_type ?? '').trim();
    if (!actionType) {
        return 'Action type is required';
    }
    const config = step.config;
    if (config !== undefined && config !== null && !configIsObject(config)) {
        return 'Action config must be a JSON object';
    }
    const required = ACTION_REQUIRED_CONFIG[actionType];
    if (!required?.length) return null;
    const cfg = configIsObject(config) ? config : {};
    for (const key of required) {
        const val = cfg[key];
        if (val === undefined || val === null || String(val).trim() === '') {
            return `Action requires config.${key}`;
        }
    }
    return null;
}

/**
 * Field-level required checks for non-action step types.
 */
export function validateStepFields(step: WorkflowStep): string | null {
    switch (step.type) {
        case 'action':
            return validateActionConfig(step);
        case 'condition':
            if (!String(step.expression ?? '').trim()) {
                return 'Condition expression is required';
            }
            return null;
        case 'wait_delay':
            if (!String(step.duration ?? '').trim()) {
                return 'Wait delay duration is required';
            }
            return null;
        case 'wait_condition':
            if (!String(step.expression ?? '').trim()) {
                return 'Wait-until expression is required';
            }
            return null;
        case 'wait_event':
            if (!String(step.event ?? '').trim()) {
                return 'Wait-event name is required';
            }
            return null;
        case 'loop':
            if (!String(step.items ?? '').trim()) {
                return 'Loop items expression is required';
            }
            return null;
        case 'parallel':
            return null;
        default:
            return null;
    }
}

/**
 * Detect free cycles among graph nodes via DFS (white/gray/black).
 * Loop/parallel step body refs are not edges — only canvas edges count.
 */
export function detectCycleNodeIds(nodes: Node[], edges: Edge[]): string[] | null {
    const ids = new Set(nodes.map((n) => n.id));
    const adj = new Map<string, string[]>();
    for (const id of ids) adj.set(id, []);
    for (const e of edges) {
        if (e.source === e.target) continue;
        if (!ids.has(e.source) || !ids.has(e.target)) continue;
        adj.get(e.source)!.push(e.target);
    }

    const WHITE = 0;
    const GRAY = 1;
    const BLACK = 2;
    const color = new Map<string, number>();
    for (const id of ids) color.set(id, WHITE);

    let cycleStart: string | null = null;
    const parent = new Map<string, string | null>();

    function dfs(u: string): boolean {
        color.set(u, GRAY);
        for (const v of adj.get(u) ?? []) {
            const c = color.get(v) ?? WHITE;
            if (c === GRAY) {
                cycleStart = v;
                parent.set(v, u);
                return true;
            }
            if (c === WHITE) {
                parent.set(v, u);
                if (dfs(v)) return true;
            }
        }
        color.set(u, BLACK);
        return false;
    }

    for (const id of ids) {
        if (color.get(id) === WHITE) {
            parent.set(id, null);
            if (dfs(id)) {
                // Reconstruct a simple cycle path for messaging
                if (cycleStart) {
                    return [cycleStart];
                }
                return [id];
            }
        }
    }
    return null;
}

/** BFS reachability from trigger along edges. */
export function reachableFromTrigger(nodes: Node[], edges: Edge[]): Set<string> {
    const ids = new Set(nodes.map((n) => n.id));
    const adj = new Map<string, string[]>();
    for (const id of ids) adj.set(id, []);
    for (const e of edges) {
        if (!ids.has(e.source) || !ids.has(e.target)) continue;
        if (e.source === e.target) continue;
        adj.get(e.source)!.push(e.target);
    }

    const start = ids.has(TRIGGER_NODE_ID) ? TRIGGER_NODE_ID : null;
    const visited = new Set<string>();
    if (!start) return visited;

    const queue = [start];
    visited.add(start);
    while (queue.length) {
        const u = queue.shift()!;
        for (const v of adj.get(u) ?? []) {
            if (!visited.has(v)) {
                visited.add(v);
                queue.push(v);
            }
        }
    }
    return visited;
}

function conditionHandles(edges: Edge[], nodeId: string): { hasTrue: boolean; hasFalse: boolean } {
    let hasTrue = false;
    let hasFalse = false;
    for (const e of edges) {
        if (e.source !== nodeId) continue;
        if (e.sourceHandle === 'true') hasTrue = true;
        else if (e.sourceHandle === 'false') hasFalse = true;
        else if (!hasTrue) hasTrue = true;
        else hasFalse = true;
    }
    return { hasTrue, hasFalse };
}

/**
 * Full graph validation. Errors block save; warnings do not.
 */
export function validateWorkflowGraph(nodes: Node[], edges: Edge[]): ValidationIssue[] {
    const issues: ValidationIssue[] = [];

    const hasTrigger = nodes.some((n) => isTriggerNode(n) || n.id === TRIGGER_NODE_ID);
    if (!hasTrigger) {
        issues.push({
            id: 'missing-trigger',
            severity: 'error',
            message: 'Workflow must have a trigger node',
        });
    }

    if (hasSelfEdges(edges)) {
        for (const e of edges) {
            if (e.source === e.target) {
                issues.push({
                    id: `self-edge-${e.id}`,
                    severity: 'error',
                    message: `Self-edge on "${e.source}" is not allowed`,
                    nodeId: e.source,
                });
            }
        }
    }

    const stepNodes = nodes.filter((n) => !isTriggerNode(n) && n.id !== TRIGGER_NODE_ID);
    const names = stepNodes.map((n) => n.id.trim());
    const nameCounts = new Map<string, number>();
    for (const name of names) {
        nameCounts.set(name, (nameCounts.get(name) ?? 0) + 1);
    }

    for (const node of stepNodes) {
        const name = node.id.trim();
        if (!name) {
            issues.push({
                id: `empty-name-${node.id}`,
                severity: 'error',
                message: 'Step name is required',
                nodeId: node.id,
            });
            continue;
        }
        if ((nameCounts.get(name) ?? 0) > 1) {
            issues.push({
                id: `dup-name-${node.id}`,
                severity: 'error',
                message: `Duplicate step name "${name}"`,
                nodeId: node.id,
            });
        }
    }

    const cycle = detectCycleNodeIds(nodes, edges);
    if (cycle) {
        issues.push({
            id: 'cycle',
            severity: 'error',
            message: 'Workflow graph contains a cycle (must be a DAG; use Loop steps for iteration)',
            nodeId: cycle[0],
        });
    }

    for (const node of stepNodes) {
        const step = stepFromNode(node);
        if (!step) continue;
        const fieldErr = validateStepFields(step);
        if (fieldErr) {
            issues.push({
                id: `field-${node.id}`,
                severity: 'error',
                message: `"${node.id}": ${fieldErr}`,
                nodeId: node.id,
            });
        }

        if (step.type === 'condition') {
            const { hasTrue, hasFalse } = conditionHandles(edges, node.id);
            if (!hasTrue || !hasFalse) {
                const missing = [
                    !hasTrue ? 'true' : null,
                    !hasFalse ? 'false' : null,
                ]
                    .filter(Boolean)
                    .join(' and ');
                issues.push({
                    id: `cond-branch-${node.id}`,
                    severity: 'warning',
                    message: `"${node.id}": condition missing ${missing} branch`,
                    nodeId: node.id,
                });
            }
        }
    }

    const reachable = reachableFromTrigger(nodes, edges);
    for (const node of stepNodes) {
        if (!reachable.has(node.id)) {
            issues.push({
                id: `orphan-${node.id}`,
                severity: 'warning',
                message: `"${node.id}" is not reachable from the trigger`,
                nodeId: node.id,
            });
        }
    }

    return issues;
}

export function hasHardErrors(issues: ValidationIssue[]): boolean {
    return issues.some((i) => i.severity === 'error');
}

export function issuesForNode(
    issues: ValidationIssue[],
    nodeId: string,
): ValidationIssue[] {
    return issues.filter((i) => i.nodeId === nodeId);
}

export function nodeIssueSeverity(
    issues: ValidationIssue[],
    nodeId: string,
): ValidationSeverity | null {
    const forNode = issuesForNode(issues, nodeId);
    if (forNode.some((i) => i.severity === 'error')) return 'error';
    if (forNode.some((i) => i.severity === 'warning')) return 'warning';
    return null;
}
