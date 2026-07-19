/**
 * Default step payloads and unique name generation for palette-created nodes.
 */

import type { WorkflowStep } from '@/services/workflows.service';
import type { StepTypeValue } from '../workflowConstants';
import { TRIGGER_NODE_ID } from '../workflowConstants';

/**
 * Generate a unique step name like `action_1`, `condition_2`.
 * Existing ids are compared case-sensitively (step names are case-sensitive in the API).
 */
export function generateUniqueStepName(
    stepType: string,
    existingIds: Iterable<string>,
): string {
    const used = new Set(existingIds);
    const prefix = stepType.replace(/[^a-z0-9_]/gi, '_') || 'step';
    let n = 1;
    while (used.has(`${prefix}_${n}`)) {
        n += 1;
    }
    return `${prefix}_${n}`;
}

/** Build a default WorkflowStep for a newly created palette node. */
export function createDefaultStep(stepType: StepTypeValue, name: string): WorkflowStep {
    const base: WorkflowStep = {
        type: stepType,
        name,
    };

    switch (stepType) {
        case 'action':
            return {
                ...base,
                action_type: 'send_webhook',
                config: {},
            };
        case 'condition':
            return {
                ...base,
                expression: '',
            };
        case 'wait_delay':
            return {
                ...base,
                duration: '5m',
            };
        case 'wait_condition':
            return {
                ...base,
                expression: '',
                poll_interval: '1m',
                timeout: '24h',
            };
        case 'wait_event':
            return {
                ...base,
                event: 'records.create',
                timeout: '24h',
            };
        case 'loop':
            return {
                ...base,
                items: '{{trigger.records}}',
                step: '',
            };
        case 'parallel':
            return {
                ...base,
                branches: [] as string[][],
            };
        default:
            return base;
    }
}

/**
 * Collect existing node ids that should not collide with new step names
 * (includes trigger id so users cannot name a step `__trigger__` via generator).
 */
export function collectNodeIds(ids: Iterable<string>): string[] {
    const list = [...ids];
    if (!list.includes(TRIGGER_NODE_ID)) {
        list.push(TRIGGER_NODE_ID);
    }
    return list;
}

/**
 * Validate action config JSON string.
 * @returns Parsed object or error message.
 */
export function parseActionConfigJson(
    raw: string,
): { ok: true; value: Record<string, unknown> } | { ok: false; error: string } {
    const trimmed = raw.trim();
    if (!trimmed) {
        return { ok: true, value: {} };
    }
    try {
        const parsed: unknown = JSON.parse(trimmed);
        if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
            return { ok: false, error: 'Config must be a JSON object' };
        }
        return { ok: true, value: parsed as Record<string, unknown> };
    } catch {
        return { ok: false, error: 'Invalid JSON' };
    }
}

/**
 * Rename a node id and rewrite all edges that reference it.
 * Returns new nodes/edges arrays (immutable).
 */
export function renameNode(
    nodes: { id: string; data?: Record<string, unknown>; [k: string]: unknown }[],
    edges: { id: string; source: string; target: string; [k: string]: unknown }[],
    oldId: string,
    newId: string,
): {
    nodes: typeof nodes;
    edges: typeof edges;
} {
    const trimmed = newId.trim();
    if (!trimmed || trimmed === oldId) {
        return { nodes, edges };
    }
    if (trimmed === TRIGGER_NODE_ID) {
        return { nodes, edges };
    }
    if (nodes.some((n) => n.id === trimmed)) {
        return { nodes, edges };
    }

    const nextNodes = nodes.map((n) => {
        if (n.id !== oldId) return n;
        const data = n.data ? { ...n.data } : {};
        if (data.kind === 'step' && data.step && typeof data.step === 'object') {
            const step = { ...(data.step as Record<string, unknown>), name: trimmed };
            return {
                ...n,
                id: trimmed,
                data: {
                    ...data,
                    label: trimmed,
                    step,
                },
            };
        }
        return { ...n, id: trimmed, data: { ...data, label: trimmed } };
    });

    const nextEdges = edges.map((e) => {
        let source = e.source;
        let target = e.target;
        let changed = false;
        if (source === oldId) {
            source = trimmed;
            changed = true;
        }
        if (target === oldId) {
            target = trimmed;
            changed = true;
        }
        if (!changed) return e;
        return {
            ...e,
            id: e.id.replaceAll(oldId, trimmed),
            source,
            target,
        };
    });

    return { nodes: nextNodes, edges: nextEdges };
}

/**
 * Remove a node and all incident edges. Trigger node is not removable.
 */
export function removeNodeAndEdges<
    N extends { id: string },
    E extends { source: string; target: string },
>(nodes: N[], edges: E[], nodeId: string): { nodes: N[]; edges: E[] } {
    if (nodeId === TRIGGER_NODE_ID) {
        return { nodes, edges };
    }
    return {
        nodes: nodes.filter((n) => n.id !== nodeId),
        edges: edges.filter((e) => e.source !== nodeId && e.target !== nodeId),
    };
}
