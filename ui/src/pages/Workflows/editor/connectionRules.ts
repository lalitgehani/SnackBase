/**
 * Connection validation and edge-construction helpers for the workflow canvas.
 */

import type { Connection, Edge, Node } from '@xyflow/react';
import { TRIGGER_NODE_ID } from '../workflowConstants';

export type ConnectionRejectReason =
    | 'self'
    | 'to_trigger'
    | 'from_missing'
    | 'duplicate'
    | 'invalid';

export interface ConnectionCheckResult {
    ok: boolean;
    reason?: ConnectionRejectReason;
}

function isConditionNode(nodes: Node[], nodeId: string): boolean {
    const n = nodes.find((x) => x.id === nodeId);
    if (!n) return false;
    if (n.type === 'condition') return true;
    const data = n.data as { step?: { type?: string }; kind?: string } | undefined;
    return data?.step?.type === 'condition';
}

/**
 * Whether a proposed connection is allowed.
 * Does not enforce single-outgoing (that is handled by replace on connect).
 */
export function validateConnection(
    connection: Connection | Edge,
    nodes: Node[],
    edges: Edge[],
): ConnectionCheckResult {
    const { source, target, sourceHandle, targetHandle } = connection;
    if (!source || !target) {
        return { ok: false, reason: 'invalid' };
    }
    if (source === target) {
        return { ok: false, reason: 'self' };
    }
    if (target === TRIGGER_NODE_ID) {
        return { ok: false, reason: 'to_trigger' };
    }
    if (!nodes.some((n) => n.id === source) || !nodes.some((n) => n.id === target)) {
        return { ok: false, reason: 'from_missing' };
    }

    const duplicate = edges.some(
        (e) =>
            e.source === source &&
            e.target === target &&
            (e.sourceHandle ?? null) === (sourceHandle ?? null) &&
            (e.targetHandle ?? null) === (targetHandle ?? null),
    );
    if (duplicate) {
        return { ok: false, reason: 'duplicate' };
    }

    return { ok: true };
}

/**
 * Apply a new connection, replacing any existing outgoing edge from the same
 * source handle (single `next`, or single true/false branch).
 */
export function applyConnection(
    connection: Connection,
    nodes: Node[],
    edges: Edge[],
): Edge[] | null {
    const check = validateConnection(connection, nodes, edges);
    if (!check.ok) {
        return null;
    }

    const { source, target, sourceHandle, targetHandle } = connection;
    if (!source || !target) return null;

    // Remove existing edge(s) from the same source handle (replace policy)
    const filtered = edges.filter((e) => {
        if (e.source !== source) return true;
        const sameHandle = (e.sourceHandle ?? null) === (sourceHandle ?? null);
        return !sameHandle;
    });

    const isCondition = isConditionNode(nodes, source);
    const handle = sourceHandle ?? undefined;

    let label: string | undefined;
    let style: Edge['style'] | undefined;
    if (isCondition && handle === 'true') {
        label = 'true';
        style = { stroke: 'var(--color-green-600, #16a34a)', strokeWidth: 1.75 };
    } else if (isCondition && handle === 'false') {
        label = 'false';
        style = { stroke: 'var(--color-red-500, #ef4444)', strokeWidth: 1.75 };
    }

    const edgeId =
        isCondition && handle
            ? `${source}->${target}:${handle}`
            : `${source}->${target}`;

    const newEdge: Edge = {
        id: edgeId,
        source,
        target,
        sourceHandle: handle,
        targetHandle: targetHandle ?? undefined,
        label,
        style,
        type: 'smoothstep',
    };

    return [...filtered, newEdge];
}

/** Style existing condition edges when loading from mapper (ensure labels/colors). */
export function decorateEdge(edge: Edge, nodes: Node[]): Edge {
    if (!isConditionNode(nodes, edge.source)) {
        return {
            ...edge,
            type: edge.type ?? 'smoothstep',
        };
    }
    if (edge.sourceHandle === 'true') {
        return {
            ...edge,
            type: edge.type ?? 'smoothstep',
            label: edge.label ?? 'true',
            style: edge.style ?? {
                stroke: 'var(--color-green-600, #16a34a)',
                strokeWidth: 1.75,
            },
        };
    }
    if (edge.sourceHandle === 'false') {
        return {
            ...edge,
            type: edge.type ?? 'smoothstep',
            label: edge.label ?? 'false',
            style: edge.style ?? {
                stroke: 'var(--color-red-500, #ef4444)',
                strokeWidth: 1.75,
            },
        };
    }
    return { ...edge, type: edge.type ?? 'smoothstep' };
}
