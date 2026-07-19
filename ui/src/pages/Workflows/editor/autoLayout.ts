/**
 * Auto-layout for workflow canvas nodes using @dagrejs/dagre.
 *
 * Default direction is left-to-right (LR) because canvas handles are on
 * Left/Right — matches the visual flow of source → target connections.
 */

import dagre from '@dagrejs/dagre';
import type { Edge, Node } from '@xyflow/react';

export type LayoutDirection = 'LR' | 'TB';

export interface LayoutOptions {
    /** Rank direction. Default: LR (left-to-right). */
    direction?: LayoutDirection;
    nodeWidth?: number;
    nodeHeight?: number;
    ranksep?: number;
    nodesep?: number;
    edgesep?: number;
    marginx?: number;
    marginy?: number;
}

const DEFAULTS = {
    direction: 'LR' as LayoutDirection,
    nodeWidth: 200,
    nodeHeight: 72,
    ranksep: 80,
    nodesep: 48,
    edgesep: 20,
    marginx: 24,
    marginy: 24,
};

/**
 * Compute new node positions via dagre. Does not mutate edges or step configs.
 * Positions are centered on the node (React Flow uses top-left origin).
 */
export function layoutGraph(
    nodes: Node[],
    edges: Edge[],
    options: LayoutOptions = {},
): Node[] {
    if (nodes.length === 0) return nodes;

    const direction = options.direction ?? DEFAULTS.direction;
    const nodeWidth = options.nodeWidth ?? DEFAULTS.nodeWidth;
    const nodeHeight = options.nodeHeight ?? DEFAULTS.nodeHeight;
    const ranksep = options.ranksep ?? DEFAULTS.ranksep;
    const nodesep = options.nodesep ?? DEFAULTS.nodesep;
    const edgesep = options.edgesep ?? DEFAULTS.edgesep;
    const marginx = options.marginx ?? DEFAULTS.marginx;
    const marginy = options.marginy ?? DEFAULTS.marginy;

    const g = new dagre.graphlib.Graph({ multigraph: true });
    g.setDefaultEdgeLabel(() => ({}));
    g.setGraph({
        rankdir: direction,
        ranksep,
        nodesep,
        edgesep,
        marginx,
        marginy,
    });

    for (const node of nodes) {
        g.setNode(node.id, { width: nodeWidth, height: nodeHeight });
    }

    // Sort edges so condition true comes before false for stable rank order
    const sortedEdges = [...edges].sort((a, b) => {
        const ha = handleOrder(a.sourceHandle);
        const hb = handleOrder(b.sourceHandle);
        if (ha !== hb) return ha - hb;
        return a.id.localeCompare(b.id);
    });

    for (const edge of sortedEdges) {
        if (!g.hasNode(edge.source) || !g.hasNode(edge.target)) continue;
        if (edge.source === edge.target) continue;
        // Prefer true branch slightly higher weight for consistent fan-out
        const weight = edge.sourceHandle === 'true' ? 2 : edge.sourceHandle === 'false' ? 1 : 1;
        g.setEdge(edge.source, edge.target, { weight }, edge.id);
    }

    dagre.layout(g);

    return nodes.map((node) => {
        const pos = g.node(node.id);
        if (!pos || !Number.isFinite(pos.x) || !Number.isFinite(pos.y)) {
            return node;
        }
        // dagre returns center; React Flow expects top-left
        return {
            ...node,
            position: {
                x: pos.x - nodeWidth / 2,
                y: pos.y - nodeHeight / 2,
            },
        };
    });
}

function handleOrder(handle: string | null | undefined): number {
    if (handle === 'true') return 0;
    if (handle === 'false') return 1;
    return 2;
}

/**
 * True when every step node is stacked at origin (legacy missing positions).
 * Trigger-only graphs return false (nothing to layout).
 */
export function shouldAutoLayoutOnLoad(nodes: Node[]): boolean {
    const steps = nodes.filter((n) => n.id !== '__trigger__' && n.type !== 'trigger');
    if (steps.length === 0) return false;
    return steps.every(
        (n) =>
            (!Number.isFinite(n.position.x) || n.position.x === 0) &&
            (!Number.isFinite(n.position.y) || n.position.y === 0),
    );
}
