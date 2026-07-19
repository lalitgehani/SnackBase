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
    let labelStyle: Edge['labelStyle'] | undefined;
    let labelBgStyle: Edge['labelBgStyle'] | undefined;
    if (isCondition && handle === 'true') {
        label = 'true';
        style = { stroke: 'var(--color-green-600, #16a34a)', strokeWidth: 1.75 };
        labelStyle = { fill: 'var(--color-green-700, #15803d)', fontWeight: 600, fontSize: 11 };
        labelBgStyle = { fill: 'var(--card, var(--background, #fff))', fillOpacity: 0.9 };
    } else if (isCondition && handle === 'false') {
        label = 'false';
        style = { stroke: 'var(--color-red-500, #ef4444)', strokeWidth: 1.75 };
        labelStyle = { fill: 'var(--color-red-600, #dc2626)', fontWeight: 600, fontSize: 11 };
        labelBgStyle = { fill: 'var(--card, var(--background, #fff))', fillOpacity: 0.9 };
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
        labelStyle,
        labelBgStyle,
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
            labelStyle: edge.labelStyle ?? {
                fill: 'var(--color-green-700, #15803d)',
                fontWeight: 600,
                fontSize: 11,
            },
            labelBgStyle: edge.labelBgStyle ?? {
                fill: 'var(--card, var(--background, #fff))',
                fillOpacity: 0.9,
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
            labelStyle: edge.labelStyle ?? {
                fill: 'var(--color-red-600, #dc2626)',
                fontWeight: 600,
                fontSize: 11,
            },
            labelBgStyle: edge.labelBgStyle ?? {
                fill: 'var(--card, var(--background, #fff))',
                fillOpacity: 0.9,
            },
        };
    }
    return { ...edge, type: edge.type ?? 'smoothstep' };
}

/**
 * Current target for a source handle (null if no outgoing edge).
 * Pass `sourceHandle` as `'true' | 'false'` for condition branches; omit for default next.
 */
export function getOutgoingTarget(
    edges: Edge[],
    sourceId: string,
    sourceHandle?: string | null,
): string | null {
    const edge = edges.find((e) => {
        if (e.source !== sourceId) return false;
        return (e.sourceHandle ?? null) === (sourceHandle ?? null);
    });
    return edge?.target ?? null;
}

/**
 * Set or clear the outgoing edge for a source handle (properties-panel wiring).
 * `targetId` null removes the edge for that handle.
 * Reuses applyConnection replace policy when setting a target.
 */
export function setOutgoingTarget(
    nodes: Node[],
    edges: Edge[],
    sourceId: string,
    targetId: string | null,
    sourceHandle?: string | null,
): Edge[] {
    const handle = sourceHandle ?? undefined;

    if (!targetId) {
        return edges.filter((e) => {
            if (e.source !== sourceId) return true;
            return (e.sourceHandle ?? null) !== (sourceHandle ?? null);
        });
    }

    const connection: Connection = {
        source: sourceId,
        target: targetId,
        sourceHandle: handle ?? null,
        targetHandle: null,
    };

    // If same edge already exists, return unchanged
    const existing = getOutgoingTarget(edges, sourceId, sourceHandle);
    if (existing === targetId) {
        // Still re-apply to ensure labels/styles
        const without = edges.filter((e) => {
            if (e.source !== sourceId) return true;
            return (e.sourceHandle ?? null) !== (sourceHandle ?? null);
        });
        const next = applyConnection(connection, nodes, without);
        return next ?? edges;
    }

    // Temporarily drop same-handle edges so validateConnection won't flag duplicate
    // when target differs (applyConnection also filters, but validate runs first)
    const withoutSameHandle = edges.filter((e) => {
        if (e.source !== sourceId) return true;
        return (e.sourceHandle ?? null) !== (sourceHandle ?? null);
    });
    const next = applyConnection(connection, nodes, withoutSameHandle);
    return next ?? edges;
}

/**
 * Default source handle when auto-wiring from a selected node after palette add.
 * Conditions use the true branch; all other nodes use the default (next) handle.
 */
export function defaultAutoConnectHandle(nodes: Node[], sourceId: string): string | undefined {
    if (isConditionNode(nodes, sourceId)) {
        return 'true';
    }
    return undefined;
}
